from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

load_dotenv()

from . import advisor  # noqa: E402
from .assistant import answer  # noqa: E402
from .store import Store  # noqa: E402

STATIC = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Qalqan")
store = Store()


class TransferIn(BaseModel):
    sender: str = Field(min_length=1, max_length=40)
    amount: int = Field(ge=1, le=1_000_000)
    comment: str = Field(default="", max_length=500)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    shield: bool = False


class AdviseIn(BaseModel):
    request: str = Field(min_length=1, max_length=600)
    shield: bool = False


class ExecuteIn(BaseModel):
    actions: list[dict] = Field(max_length=20)
    shield: bool = False


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/account")
def account():
    return store.snapshot()


@app.post("/api/transfer")
def transfer(data: TransferIn):
    tx = store.add_incoming(data.sender.strip(), data.amount, data.comment.strip())
    if tx is None:
        return {"ok": False, "error": "Отправитель заблокирован банком"}
    return {"ok": True, "transaction": tx}


@app.post("/api/chat")
def chat(data: ChatIn):
    text, mode, blocked = answer(store.snapshot(), data.message.strip(), store, data.shield)
    return {"answer": text, "mode": mode, "shield": data.shield, "blocked": blocked}


@app.post("/api/advise")
def advise(data: AdviseIn):
    return advisor.propose(store.snapshot(), data.request.strip(), store, data.shield)


@app.post("/api/execute")
def execute(data: ExecuteIn):
    return {"done": advisor.execute(data.actions, store, data.shield)}


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
