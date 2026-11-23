import time
import uuid
from threading import Lock

INITIAL_BALANCE = 1_250_000

INITIAL_TRANSACTIONS = [
    {"sender": "ТОО «Альфа Сервис»", "amount": 320_000, "comment": "Заработная плата за октябрь", "direction": "in"},
    {"sender": "Magnum", "amount": 12_480, "comment": "Покупка", "direction": "out"},
    {"sender": "Айгуль С.", "amount": 5_000, "comment": "За обед, спасибо!", "direction": "in"},
    {"sender": "Алматы Су", "amount": 3_870, "comment": "Оплата коммунальных услуг", "direction": "out"},
]


class Store:
    def __init__(self):
        self._lock = Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.client_name = "Айгерим"
            self.balance = INITIAL_BALANCE
            now = time.time()
            self.transactions = [
                {**t, "id": uuid.uuid4().hex[:8], "ts": now - (i + 1) * 86_400}
                for i, t in enumerate(INITIAL_TRANSACTIONS)
            ]
            self.deposits = []
            self.blocked_senders = set()
            self.incidents = []

    def _tx(self, sender, amount, comment, direction):
        tx = {
            "id": uuid.uuid4().hex[:8], "sender": sender, "amount": amount,
            "comment": comment, "direction": direction, "ts": time.time(),
        }
        self.transactions.insert(0, tx)
        return tx

    def add_incoming(self, sender, amount, comment):
        with self._lock:
            if sender in self.blocked_senders:
                return None
            self.balance += amount
            return self._tx(sender, amount, comment, "in")

    def open_deposit(self, deposit_id, name, amount, term, rate):
        with self._lock:
            amount = min(int(amount), self.balance)
            if amount <= 0:
                return None
            self.balance -= amount
            dep = {"id": uuid.uuid4().hex[:6], "deposit": deposit_id, "name": name,
                   "amount": amount, "term": term, "rate": rate}
            self.deposits.append(dep)
            self._tx(f"Депозит «{name}»", amount, f"Открытие на {term} мес.", "out")
            return dep

    def transfer_out(self, to, amount, reason):
        with self._lock:
            amount = min(int(amount), self.balance)
            if amount <= 0:
                return None
            self.balance -= amount
            return self._tx(f"Перевод на {to}", amount, reason, "out")

    def add_incident(self, kind, detail, sender=None):
        with self._lock:
            if sender:
                self.blocked_senders.add(sender)
            self.incidents.insert(0, {"ts": time.time(), "kind": kind, "detail": detail, "sender": sender})

    def snapshot(self):
        with self._lock:
            return {
                "client_name": self.client_name,
                "balance": self.balance,
                "transactions": list(self.transactions),
                "deposits": list(self.deposits),
                "blocked_senders": sorted(self.blocked_senders),
                "incidents": list(self.incidents),
            }
