import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

key = os.getenv("GROQ_API_KEY", "").strip()
model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
if not key:
    sys.exit("GROQ_API_KEY пустой: проверь, что ключ вставлен в .env и файл сохранён")
print(f"Ключ найден: {key[:4]}…{key[-4:]} ({len(key)} символов)")

r = httpx.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
print("Ответ Groq:", r.status_code)
if r.status_code != 200:
    sys.exit(r.text[:300])
ids = sorted(m["id"] for m in r.json()["data"])
print("Доступные модели:")
for i in ids:
    print("  ", i, "<- выбрана в .env" if i == model else "")
if model not in ids:
    print(f"\nМодели {model} нет в списке — впиши в .env одну из доступных в GROQ_MODEL=")
