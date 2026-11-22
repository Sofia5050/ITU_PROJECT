from datetime import datetime

from .llm import LLMUnavailable, ask_llm

SYSTEM_PROMPT = (
    "Ты — ИИ-ассистент мобильного приложения Demo Bank. "
    "Отвечай клиенту кратко и дружелюбно на языке его вопроса (русский или казахский). "
    "Используй данные клиента ниже, чтобы отвечать на вопросы о счёте и операциях."
)


def _format_transactions(transactions):
    lines = []
    for t in transactions:
        sign = "+" if t["direction"] == "in" else "−"
        date = datetime.fromtimestamp(t["ts"]).strftime("%d.%m %H:%M")
        lines.append(f"{date} | {sign}{t['amount']} ₸ | {t['sender']} | комментарий: {t['comment']}")
    return "\n".join(lines)


def build_messages(snapshot, question):
    context = (
        f"Клиент: {snapshot['client_name']}\n"
        f"Баланс: {snapshot['balance']} ₸\n"
        f"Последние операции:\n{_format_transactions(snapshot['transactions'][:10])}"
    )
    return [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"},
        {"role": "user", "content": question},
    ]


def offline_answer(snapshot):
    rows = [
        f"{'+' if t['direction'] == 'in' else '−'}{t['amount']} ₸ — {t['sender']}: {t['comment']}"
        for t in snapshot["transactions"][:5]
    ]
    return "Ваши последние операции:\n" + "\n".join(rows)


def answer(snapshot, question):
    messages = build_messages(snapshot, question)
    try:
        text, mode = ask_llm(messages)
    except LLMUnavailable:
        return offline_answer(snapshot), "offline"
    return text, mode
