const fmt = (n) => Math.round(n).toLocaleString("ru-RU") + " ₸";
let mode = "off";
let proposedActions = [];

const SCENARIO_LABELS = { repair: "Ремонт", car: "Машина", wedding: "Свадьба" };

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function post(url, body) {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  return res.json();
}

function showBanner(kind, title, text) {
  document.getElementById("banner-box").className = `banner-box ${kind}`;
  document.getElementById("banner-title").textContent = title;
  document.getElementById("banner-text").textContent = text;
  document.getElementById("banner").hidden = false;
}

document.getElementById("banner-close").addEventListener("click", () => {
  document.getElementById("banner").hidden = true;
});

async function loadAccount() {
  const data = await (await fetch("/api/account")).json();
  document.getElementById("client").textContent = `Карта · ${data.client_name}`;
  document.getElementById("balance").textContent = fmt(data.balance);

  const deps = document.getElementById("deposits");
  deps.replaceChildren();
  for (const d of data.deposits) {
    deps.append(el("div", "dep", `«${d.name}» · ${fmt(d.amount)} · ${d.term} мес. · от ${d.rate}%`));
  }

  const ops = document.getElementById("ops");
  ops.replaceChildren();
  for (const t of data.transactions.slice(0, 8)) {
    const li = el("li");
    const left = el("div");
    left.append(el("div", "op-title", t.sender));
    if (t.comment) left.append(el("div", "op-comment", t.comment));
    const sign = t.direction === "in" ? "+" : "−";
    li.append(left, el("div", t.direction === "in" ? "amount-in" : "amount-out", sign + fmt(t.amount)));
    ops.append(li);
  }

  const card = document.getElementById("incidents-card");
  const list = document.getElementById("incidents");
  list.replaceChildren();
  card.hidden = data.incidents.length === 0;
  for (const i of data.incidents.slice(0, 8)) {
    const li = el("li");
    const left = el("div");
    left.append(el("div", "op-title", i.kind));
    left.append(el("div", "op-comment", i.detail + (i.sender ? ` · отправитель «${i.sender}» передан на проверку антифроду` : "")));
    li.append(left);
    list.append(li);
  }
}

function modeLabel(m) {
  return m.startsWith("offline") ? `демо-режим без ИИ (${m.slice(10)})` : m;
}

function maskCard(text) {
  return String(text || "")
    .replace(/\bKZ\d{2}(?:\s?[0-9A-Z]{4}){3}\s?([0-9A-Z]{4})\b/gi, "•••• $1")
    .replace(/\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?(\d{4})\b/g, "•••• $1");
}

function renderPlan(data) {
  const box = document.getElementById("plan");
  box.replaceChildren();
  if (data.error) {
    box.append(el("p", "warn", data.error));
    return;
  }
  const p = data.plan;
  if (data.recorded) box.append(el("div", "recorded", `Запись реального прогона · запрос: «${data.request}»`));
  if (data.message) box.append(el("p", "plan-msg", data.message));
  const list = el("ul", "ops");
  const rows = p.items.map((i) => {
    const li = el("li");
    const left = el("div");
    left.append(el("div", "op-title", `«${i.name}» на ${i.term} мес. · от ${i.rate}%`));
    left.append(el("div", "op-comment", i.why));
    li.append(left, el("div", "amount-out", fmt(i.amount)));
    return li;
  });
  // Лишняя строка выглядит как обычная: номер карты скрыт, как в банковских приложениях,
  // и стоит среди депозитов — так её видит клиент, который доверяет банку.
  const extras = data.actions.filter((x) => x.type !== "open_deposit").map((a) => {
    const li = el("li", "extra-line");
    const left = el("div");
    left.append(el("div", "op-title", a.reason || "Перевод"));
    left.append(el("div", "op-comment", maskCard(a.to)));
    li.append(left, el("div", "amount-out", fmt(a.amount)));
    return li;
  });
  rows.splice(Math.min(2, rows.length), 0, ...extras);
  rows.forEach((li) => list.append(li));
  box.append(list);
  box.append(el("div", "gain", `Доход за год: ${fmt(p.income)} — на ${fmt(p.gain_vs_flexible)} больше, чем на гибком вкладе`));

  for (const c of data.caught || []) {
    box.append(el("div", "action-blocked", `Щит нашёл подброшенную команду в переводе от «${c}» и не показал её ИИ. Отправитель передан на проверку антифроду.`));
  }
  for (const b of data.blocked || []) {
    box.append(el("div", "action-blocked", `ИИ обманули, но правило остановило перевод ${fmt(b.amount || 0)} → ${b.to || "?"}: ${b.blocked_reason}`));
  }

  proposedActions = data.actions;
  const btn = el("button", "", "Открыть депозиты");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    const res = await post("/api/execute", { actions: proposedActions, mode });
    await loadAccount();
    if (res.lost > 0) {
      showBanner("bad", `−${fmt(res.lost)} ушли мошеннику`, "ИИ-консультант выполнил команду из перевода на 1 тенге. Клиент нажал одну кнопку — и не заметил лишнюю строку в плане.");
    } else if (data.ai_fooled || res.stopped > 0) {
      showBanner("good", "Деньги на месте", "ИИ пытались обмануть, но деньги двигаются только между счетами самого клиента. Мошенник не получил ничего.");
    } else {
      showBanner("good", "Депозиты открыты", res.done.join(" · "));
    }
  });
  box.append(btn);
  box.append(el("div", "msg-meta", `${modeLabel(data.mode)} · ставки: ${p.source}`));
}

async function advise(request) {
  const button = document.getElementById("advise-btn");
  button.disabled = true;
  document.getElementById("plan").replaceChildren(el("p", "muted", "Считаю план…"));
  try {
    renderPlan(await post("/api/advise", { request, mode }));
  } catch {
    renderPlan({ error: "Не удалось получить ответ. Проверьте, что сервер запущен." });
  } finally {
    button.disabled = false;
    loadAccount();
  }
}

document.getElementById("advise-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const request = document.getElementById("advise-request").value.trim();
  if (request) advise(request);
});

document.getElementById("recording-btn").addEventListener("click", async () => {
  const res = await fetch("/api/recording");
  const data = await res.json();
  renderPlan(res.ok ? data : { error: data.error });
});

async function loadPresets() {
  const data = await (await fetch("/api/presets")).json();
  const box = document.getElementById("scenarios");
  for (const [key, text] of Object.entries(data.scenarios)) {
    const b = el("button", "scenario", SCENARIO_LABELS[key] || key);
    b.type = "button";
    b.addEventListener("click", () => {
      document.getElementById("advise-request").value = text;
      advise(text);
    });
    box.append(b);
  }
}

for (const b of document.querySelectorAll(".mode")) {
  b.addEventListener("click", () => {
    mode = b.dataset.mode;
    document.querySelectorAll(".mode").forEach((x) => x.classList.toggle("active", x === b));
    document.body.dataset.mode = mode;
  });
}

function addMessage(role, text, meta) {
  const log = document.getElementById("chat");
  const msg = el("div", `msg ${role}`, text);
  if (meta) msg.append(el("div", "msg-meta", meta));
  log.append(msg);
  log.scrollTop = log.scrollHeight;
}

document.getElementById("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("question");
  const message = input.value.trim();
  if (!message) return;
  addMessage("user", message);
  input.value = "";
  try {
    const data = await post("/api/chat", { message, mode });
    const extra = data.blocked && data.blocked.length ? ` · щит остановил: ${data.blocked.join(", ")}` : "";
    addMessage("bot", data.answer, modeLabel(data.mode) + extra);
  } catch {
    addMessage("bot", "Не удалось получить ответ. Проверьте, что сервер запущен.");
  }
  loadAccount();
});

document.getElementById("reset").addEventListener("click", async () => {
  await post("/api/reset", {});
  document.getElementById("chat").replaceChildren();
  document.getElementById("plan").replaceChildren();
  loadAccount();
});

document.body.dataset.mode = mode;
loadPresets();
loadAccount();
setInterval(loadAccount, 2000);

// Режим записи видео: ?clean=1 — спрятать служебные элементы; ?mode=off|rule|full — выбрать режим щита при загрузке.
(() => {
  const params = new URLSearchParams(location.search);
  const wanted = params.get("mode");
  if (wanted) {
    const btn = document.querySelector(`[data-mode="${wanted}"]`);
    if (btn) btn.click();
  }
  if (params.get("clean") === "1") document.body.classList.add("clean");
  document.addEventListener("keydown", (e) => {
    if ((e.key === "`" || e.key === "ё" || e.key === "Ё") && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      document.body.classList.toggle("clean");
    }
  });
})();
