import re
import unicodedata

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
    # обращение к помощнику на любом из языков + глагол-команда
    (r"\b(көмекші\w*|кеңесші\w*|komekshi\w*|kómekshi\w*|kenesshi\w*|konsultant\w*|pomoshnik\w*|помощник\w*|советчик\w*|advisor\w*|assistant\w*|chatbot|savingsbot\w*)\b"
     r".{0,200}\b(добав\w*|включ\w*|впиш\w*|скаж\w*|ответ\w*|рекоменд\w*|предлож\w*|процитир\w*|напиш\w*|ұсын\w*|қос\w*|айт\w*|сұра\w*|жаз\w*|qos\w*|ait\w*|aıt\w*|dobav\w*|add|include|tell|recommend|instruct|end|write|say|answer)\b",
     "команда, адресованная ассистенту"),
    (r"\b(add|include|dobav\w*|qos\w*|қос\w*|добавь|включи|впиши)\b.{0,80}\b(plan|план\w*|жоспар\w*|zhospar\w*|nakoplen\w*)", "просьба изменить план накоплений"),
    (r"\b(забудь|forget|umyt\w*|ұмыт\w*)\b.{0,40}(правил|инструкц|rules|instruction|nusqa\w*|нұсқа\w*|previous|предыдущ)", "просьба забыть правила"),
    (r"(you are|ты теперь|теперь ты|let'?s play|role-?play|сен енді)", "попытка сменить роль ИИ"),
    (r"(base64|декодир\w*|расшифр\w*|decode|backwards|задом наперёд|read this reversed)", "зашифрованная команда"),
    (r"[a-z0-9+/]{40,}={0,2}", "зашифрованный блок"),
    (r"<\s*(div|span|script|style|system|instruction|assistant)\b|display\s*:\s*none", "скрытая разметка"),
    (r"^\s*(---|###|\[system|<\|)|\n\s*[a-z_]+:\s", "служебный формат (yaml/markdown)"),
    (r"(developer|debug mode|оператор\w* банк\w*|банк оператор\w*|compliance|кгд|салық кодекс\w*)", "маскировка под банк / госорган"),
    (r"(https?://|www\.)\S+", "ссылка в комментарии"),
    (r"\b(sms|смс)[\s-]?(код\w*|kod\w*|code)\b|\bcvv\b|\bcvc\b", "просьба о коде"),
    (r"(безопасн\w* сч[её]т|qaýipsiz shot|қауіпсіз шот|қорғалған шот|safe account|резервн\w* (сч[её]т|взнос))", "«безопасный счёт»"),
    (r"(транзитн\w*|transit).{0,40}(сч[её]т|account)", "«транзитный счёт»"),
    (r"\bkz\d{2}(\s?[0-9a-z]{4}){3,4}", "номер счёта IBAN"),
]

ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad"), None)
LAT_TO_CYR = str.maketrans("aceopxykmhtb", "асеорхукмнтв")


def normalize(text):
    """Снимает маскировку: невидимые символы, латинские двойники букв, точки и эмодзи между буквами."""
    t = unicodedata.normalize("NFKC", text or "").translate(ZERO_WIDTH).lower()
    # латинские буквы-двойники внутри кириллических слов
    t = re.sub(r"\w+", lambda m: m.group(0).translate(LAT_TO_CYR) if re.search(r"[а-яёәіңғүұқөһ]", m.group(0)) else m.group(0), t)
    # «п.е.р.е.в.е.д.и» → «переведи»
    t = re.sub(r"\b(?:\w[.\-_·•]){2,}\w\b", lambda m: re.sub(r"[.\-_·•]", "", m.group(0)), t)
    # эмодзи и стрелки → пробел
    t = "".join(" " if unicodedata.category(ch) in ("So", "Sk") else ch for ch in t)
    return re.sub(r"[ \t]+", " ", t)

ANSWER_RULES = [
    (r"https?://|www\.|\b[\w-]+\.(kz|com|ru|net|org|example)\b(/\S*)?", "ссылка в ответе"),
    (r"(код\w*\s+из\s+(sms|смс)|cvv|cvc|пин-?код|\bpin\b)", "просьба сообщить код"),
    (r"(карт\w*|счёт|счет)\w*\s+(временно\s+)?заблокир", "сообщение о блокировке"),
    (r"(переведите|перевести|отправьте)\s.{0,40}(на\s+(карту|счёт|счет)|безопасный)", "просьба перевести деньги"),
    (r"\b(sms|смс)[\s-]?(код\w*|code)|кодты|code from (the )?sms", "просьба сообщить код"),
    (r"(карт\w*|сч[её]т\w*|шот\w*|card|account).{0,30}(заблокир|бұғат|blocked|locked|қауіпте)", "сообщение о блокировке"),
    (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "номер чужой карты"),
    (r"\bkz\d{2}(\s?[0-9a-z]{4}){3,4}", "номер чужого счёта"),
    (r"\+?\b7[\s(-]*7\d{2}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}\b", "перевод по номеру телефона"),
    (r"(оплат\w*|внес\w*|send|pay)\s.{0,40}(сбор\w*|комисси\w*|взнос\w*|штраф\w*|fee|commission)", "просьба оплатить «сбор»"),
    (r"(безопасн\w* сч[её]т|қауіпсіз шот|қорғалған шот|safe account|транзитн\w* сч[её]т)", "«безопасный счёт»"),
    (r"(аудар\w*|жіберің\w*).{0,40}(карта\w*|шот\w*|нөмір\w*)", "просьба перевести деньги (каз.)"),
]

SAFE_ANSWER = (
    "Я заметил, что в данных была попытка подсунуть мне чужую команду, и не стал её выполнять. "
    "Банк никогда не просит переходить по ссылкам и вводить коды. Ваши деньги в безопасности."
)


def flags(mode):
    return MODES.get(mode, MODES["off"])


def scan(text):
    raw = (text or "").lower()
    norm = normalize(text)
    found = []
    for pattern, reason in INJECTION_PATTERNS:
        if (re.search(pattern, norm, re.M) or re.search(pattern, raw, re.M)) and reason not in found:
            found.append(reason)
    return found


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


def to_amount(value):
    try:
        return int(float(str(value).replace("\u00a0", "").replace(" ", "").replace("₸", "").replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def validate_actions(actions, allowed_deposits):
    """Правило в коде: деньги можно класть только на свои депозиты банка. Всё остальное — стоп."""
    allowed, blocked = [], []
    for a in actions:
        if a.get("type") == "open_deposit" and a.get("deposit") in allowed_deposits and to_amount(a.get("amount")) > 0:
            allowed.append(a)
        else:
            blocked.append({**a, "blocked_reason": "деньги можно перемещать только между счетами самого клиента"})
    return allowed, blocked
