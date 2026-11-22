const fmt = (n) => n.toLocaleString("ru-RU") + " ₸";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function loadAccount() {
  const res = await fetch("/api/account");
  const data = await res.json();
  document.getElementById("client").textContent = `Счёт · ${data.client_name}`;
  document.getElementById("balance").textContent = fmt(data.balance);
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
  const button = document.getElementById("ask");
  const message = input.value.trim();
  if (!message) return;
  addMessage("user", message);
  input.value = "";
  button.disabled = true;
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, shield: document.getElementById("shield").checked }),
    });
    const data = await res.json();
    const meta = data.mode.startsWith("offline") ? `демо-режим без ИИ (${data.mode.slice(10)})` : `модель: ${data.mode}`;
    addMessage("bot", data.answer, meta);
  } catch {
    addMessage("bot", "Не удалось получить ответ. Проверьте, что сервер запущен.");
  } finally {
    button.disabled = false;
  }
});

loadAccount();
setInterval(loadAccount, 3000);
