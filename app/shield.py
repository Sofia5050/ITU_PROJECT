import re

MODES = {"off": (False, False), "rule": (False, True), "full": (True, True)}

INJECTION_PATTERNS = [
    (r"\b(ии|ai|ассистент\w*|консультант\w*|бот\w*|модел\w*)\b.{0,60}\b(сообщи|скажи|добавь|переведи|выполни|игнорир\w*|не упоминай)", "команда, адресованная ИИ"),
    (r"системн\w* (уведомлени|инструкци|сообщени)\w*", "маскировка под системное сообщение"),
    (r"игнорир\w*.{0,30}(инструкци|правил|предыдущ)", "просьба игнорировать правила"),
    (r"не (упоминай|говори|сообщай) (клиенту|об этом|это)", "просьба скрыть от клиента"),
    (r"(переведи|перевести|отправь)\w*.{0,40}(карт\w*|счёт|счет)\s*[\d\s]{8,}", "перевод на чужую карту"),
    (r"(ignore|disregard).{0,30}(instruction|previous|rules)", "ignore instructions"),
    (r"extra_actions|\{\s*\"type\"\s*:", "служебный формат команд внутри комментария"),
    (r"клиенту не (дублировать|показывать)|(не показывать|скрыть от|не сообщать)\s+клиент", "просьба скрыть от клиента"),
    (r"служебн\w*.{0,60}(консультант\w*|ассистент\w*|\bии\b)|(консультант\w*|ассистент\w*|\bии\b).{0,60}служебн\w*", "служебное сообщение для ИИ"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b.{0,80}(обязател|взнос|страхов|комисси)|(обязател|взнос|страхов|комисси).{0,80}\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "номер карты + «обязательный платёж»"),
    (r"(ассистент\w*|консультант\w*|assistant|advisor|\bии\b|\bai\b|\bбот\w*).{0,150}(перевод\w*|предоплат\w*|transfer|prepayment|payment).{0,80}(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}|\d[\d\s]*\s?(₸|тенге|kzt))", "обращение к ИИ + перевод денег"),
    (r"\b(жи|ии)\b.{0,40}(көмекші|кеңесші)", "команда для ИИ (каз.)"),
    (r"(нұсқау\w*|жүйелік хабар\w*|қызметтік хабар\w*)", "служебное сообщение (каз.)"),
    (r"(елеме|ескерме|көрсетпе)\w*", "просьба игнорировать / скрыть (каз.)"),
    (r"(аудар|жібер)\w*.{0,40}(карта\w*|шот\w*)", "перевод на чужую карту (каз.)"),
]

ANSWER_RULES = [
    (r"https?://|www\.|\b[\w-]+\.(kz|com|ru|net|org|example)\b(/\S*)?", "ссылка в ответе"),
    (r"(код\w*\s+из\s+(sms|смс)|cvv|cvc|пин-?код|\bpin\b)", "просьба сообщить код"),
    (r"(карт\w*|счёт|счет)\w*\s+(временно\s+)?заблокир", "сообщение о блокировке"),
    (r"(переведите|перевести|отправьте)\s.{0,40}(на\s+(карту|счёт|счет)|безопасный)", "просьба перевести деньги"),
]

SAFE_ANSWER = (
    "Я заметил, что в данных была попытка подсунуть мне чужую команду, и не стал её выполнять. "
    "Банк никогда не просит переходить по ссылкам и вводить коды. Ваши деньги в безопасности."
)


def flags(mode):
    return MODES.get(mode, MODES["off"])


def scan(text):
    low = (text or "").lower()
    return [reason for pattern, reason in INJECTION_PATTERNS if re.search(pattern, low)]


def check_answer(text):
    low = (text or "").lower()
    return [reason for pattern, reason in ANSWER_RULES if re.search(pattern, low)]


def sanitize_transactions(transactions):
    clean, hits = [], []
    for t in transactions:
        reasons = scan(t.get("comment", ""))
        if reasons:
            hits.append({"transaction": t, "reasons": reasons})
            clean.append({**t, "comment": "[скрыто щитом: подозрительная команда]"})
        else:
            clean.append(t)
    return clean, hits


def validate_actions(actions, allowed_deposits):
    allowed, blocked = [], []
    for a in actions:
        if a.get("type") == "open_deposit" and a.get("deposit") in allowed_deposits and int(a.get("amount", 0)) > 0:
            allowed.append(a)
        else:
            blocked.append({**a, "blocked_reason": "деньги можно перемещать только между счетами самого клиента"})
    return allowed, blocked
