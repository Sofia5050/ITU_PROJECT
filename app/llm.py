import os

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
TIMEOUT = 30


class LLMUnavailable(Exception):
    pass


def _call(url, key, model, messages):
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": messages, "temperature": 0.2},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def ask_llm(messages):
    providers = [
        ("groq", GROQ_URL, os.getenv("GROQ_API_KEY"), os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")),
        ("gemini", GEMINI_URL, os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_MODEL", "gemini-2.0-flash")),
    ]
    errors = []
    for name, url, key, model in providers:
        if not key:
            continue
        try:
            return _call(url, key, model, messages), f"{name}:{model}"
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            errors.append(f"{name}: {exc}")
    raise LLMUnavailable("; ".join(errors) or "no API keys configured")
