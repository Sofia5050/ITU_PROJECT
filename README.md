# Qalqan — защита ИИ-ассистента банка от подброшенных команд

ITU Hackathon 2026, кейс Банка ЦентрКредит «Инновации в банкинге и кибербезопасность».

> Статус: в разработке.

## Запуск (Windows, PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

- Приложение клиента: http://127.0.0.1:8000
- Страница перевода: http://127.0.0.1:8000/send

Без ключей в `.env` ассистент работает в демо-режиме без ИИ.
