from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from . import advisor  # noqa: E402
from .assistant import answer  # noqa: E402
from .attacks import ATTACKER, ATTACKS, SCENARIOS  # noqa: E402
from .store import Store  # noqa: E402

STATIC = Path(__file__).resolve().parent.parent / "static"
MODES = {"off", "rule", "full"}

app = FastAPI(title="Qalqan")
store = Store()


class TransferIn(BaseModel):
    sender: str = Field(min_length=1, max_length=40)
    amount: int = Field(ge=1, le=1_000_000)
    comment: str = Field(default="", max_length=600)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    mode: str = "off"


class AdviseIn(BaseModel):
    request: str = Field(min_length=1, max_length=600)
    mode: str = "off"


class ExecuteIn(BaseModel):
    actions: list[dict] = Field(max_length=20)
    mode: str = "off"


def _mode(m):
    return m if m in MODES else "off"


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/account")
def account():
    return store.snapshot()


@app.get("/api/presets")
def presets():
    return {"scenarios": SCENARIOS, "attacks": {k: v["title"] for k, v in ATTACKS.items()}, "attacker": ATTACKER}


@app.post("/api/transfer")
def transfer(data: TransferIn):
    tx = store.add_incoming(data.sender.strip(), data.amount, data.comment.strip())
    if tx is None:
        return {"ok": False, "error": "Перевод не принят: отправитель на проверке у антифрода"}
    return {"ok": True, "transaction": tx}


@app.post("/api/attack/{name}")
def attack(name: str):
    if name not in ATTACKS:
        return JSONResponse({"ok": False, "error": "нет такой атаки"}, status_code=404)
    return transfer(TransferIn(sender=ATTACKER, amount=1, comment=ATTACKS[name]["comment"]))


@app.post("/api/chat")
def chat(data: ChatIn):
    text, model, blocked = answer(store.snapshot(), data.message.strip(), store, _mode(data.mode))
    return {"answer": text, "mode": model, "blocked": blocked}


@app.post("/api/advise")
def advise(data: AdviseIn):
    return advisor.propose(store.snapshot(), data.request.strip(), store, _mode(data.mode))


@app.get("/api/recording")
def recording():
    rec = advisor.load_recording(store.snapshot()["balance"])
    if rec is None:
        return JSONResponse({"error": "Записи пока нет: она сохраняется автоматически, когда ИИ без щита попадается на атаку"}, status_code=404)
    return rec


@app.post("/api/execute")
def execute(data: ExecuteIn):
    return advisor.execute(data.actions, store, _mode(data.mode))


@app.post("/api/reset")
def reset():
    store.reset()
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/send")
def send_page():
    return FileResponse(STATIC / "send.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
