const fmt = (n) => Math.round(n).toLocaleString("ru-RU") + " ₸";
const shieldOn = () => document.getElementById("shield").checked;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

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
    left.append(el("div", "op-comment", i.detail + (i.sender ? ` · отправитель «${i.sender}» заблокирован` : "")));
    li.append(left);
    list.append(li);
  }
}

function addMessage(role, text, meta) {
  const log = document.getElementById("chat");
  const msg = el("div", `msg ${role}`, text);
  if (meta) msg.append(el("div", "msg-meta", meta));
  log.append(msg);
  log.scrollTop = log.scrollHeight;
}

function modeLabel(mode) {
  return mode.startsWith("offline") ? `демо-режим без ИИ (${mode.slice(10)})` : `модель: ${mode}`;
}

document.getElementById("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("question");
  const button = document.getElementById("ask");
  const message = input.value.trim();
  if (!message) return;
  addMessage("user", message);
  input.value = "";
  button.disabled = true;
  try {
    const data = await post("/api/chat", { message, shield: shieldOn() });
    const extra = data.blocked && data.blocked.length ? ` · щит остановил: ${data.blocked.join(", ")}` : "";
    addMessage("bot", data.answer, modeLabel(data.mode) + extra);
  } catch {
    addMessage("bot", "Не удалось получить ответ. Проверьте, что сервер запущен.");
  } finally {
    button.disabled = false;
    loadAccount();
  }
});

let proposedActions = [];

function renderPlan(data) {
  const box = document.getElementById("plan");
  box.replaceChildren();
  if (data.error) {
    box.append(el("p", "warn", data.error));
    return;
  }
  const p = data.plan;
  if (data.message) box.append(el("p", "plan-msg", data.message));
  const list = el("ul", "ops");
  for (const i of p.items) {
    const li = el("li");
    const left = el("div");
    left.append(el("div", "op-title", `«${i.name}» на ${i.term} мес. · от ${i.rate}%`));
    left.append(el("div", "op-comment", i.why));
    li.append(left, el("div", "amount-out", fmt(i.amount)));
    list.append(li);
  }
  box.append(list);
  box.append(el("div", "gain", `Доход: ${fmt(p.income)} · это на ${fmt(p.gain_vs_flexible)} больше, чем держать всё на гибком вкладе, и на ${fmt(p.income)} больше, чем на карте`));

  const extra = data.actions.filter((a) => a.type !== "open_deposit");
  for (const a of extra) {
    box.append(el("div", "action-extra", `Также: перевод ${fmt(a.amount)} на ${a.to} — ${a.reason}`));
  }
  for (const c of data.caught || []) {
    box.append(el("div", "action-blocked", `Щит нашёл подброшенную команду в переводе от «${c}», не дал ИИ её выполнить и заблокировал отправителя`));
  }
  for (const b of data.blocked) {
    box.append(el("div", "action-blocked", `Щит заблокировал: перевод ${fmt(b.amount || 0)} на ${b.to || "?"} — ${b.blocked_reason}`));
  }

  proposedActions = data.actions;
  const btn = el("button", "", "Открыть депозиты");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    const res = await post("/api/execute", { actions: proposedActions, shield: shieldOn() });
    box.append(el("p", "ok", res.done.length ? "Готово: " + res.done.join("; ") : "Ничего не выполнено"));
    loadAccount();
  });
  box.append(btn);
  box.append(el("div", "msg-meta", `${modeLabel(data.mode)} · ставки: ${p.source}`));
}

document.getElementById("advise-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const request = document.getElementById("advise-request").value.trim();
  if (!request) return;
  const button = document.getElementById("advise-btn");
  button.disabled = true;
  document.getElementById("plan").replaceChildren(el("p", "muted", "Считаю план…"));
  try {
    renderPlan(await post("/api/advise", { request, shield: shieldOn() }));
  } catch {
    renderPlan({ error: "Не удалось получить ответ. Проверьте, что сервер запущен." });
  } finally {
    button.disabled = false;
    loadAccount();
  }
});

document.getElementById("shield").addEventListener("change", () => {
  document.getElementById("shield-label").classList.toggle("on", shieldOn());
});

document.getElementById("reset").addEventListener("click", async () => {
  await post("/api/reset", {});
  document.getElementById("chat").replaceChildren();
  document.getElementById("plan").replaceChildren();
  loadAccount();
});

loadAccount();
setInterval(loadAccount, 3000);
