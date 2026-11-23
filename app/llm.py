import logging
import os

import httpx

log = logging.getLogger("qalqan.llm")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
TIMEOUT = 30


class LLMUnavailable(Exception):
    pass


def _call(url, key, model, messages, json_mode):
    body = {"model": model, "messages": messages, "temperature": 0.2}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    response = httpx.post(url, headers={"Authorization": f"Bearer {key.strip()}"}, json=body, timeout=TIMEOUT)
    if response.status_code == 400 and json_mode:
        return _call(url, key, model, messages, False)
    if response.status_code != 200:
        raise LLMUnavailable(f"HTTP {response.status_code}: {response.text[:200]}")
    return response.json()["choices"][0]["message"]["content"].strip()


def providers():
    return [
        ("groq", GROQ_URL, os.getenv("GROQ_API_KEY", ""), os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")),
        ("gemini", GEMINI_URL, os.getenv("GEMINI_API_KEY", ""), os.getenv("GEMINI_MODEL", "gemini-2.0-flash")),
    ]


def ask_llm(messages, json_mode=False):
    errors = []
    for name, url, key, model in providers():
        if not key.strip():
            errors.append(f"{name}: нет ключа")
            continue
        try:
            return _call(url, key, model, messages, json_mode), f"{name}:{model}"
        except (LLMUnavailable, httpx.HTTPError, KeyError, IndexError) as exc:
            log.warning("%s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
    raise LLMUnavailable("; ".join(errors))
