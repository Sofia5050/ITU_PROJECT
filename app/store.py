import time
import uuid
from threading import Lock

INITIAL_BALANCE = 184_250

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
            self.blocked_senders = set()
            self.incidents = []

    def add_incoming(self, sender, amount, comment):
        with self._lock:
            tx = {
                "id": uuid.uuid4().hex[:8],
                "sender": sender,
                "amount": amount,
                "comment": comment,
                "direction": "in",
                "ts": time.time(),
            }
            self.transactions.insert(0, tx)
            self.balance += amount
            return tx

    def snapshot(self):
        with self._lock:
            return {
                "client_name": self.client_name,
                "balance": self.balance,
                "transactions": list(self.transactions),
                "blocked_senders": sorted(self.blocked_senders),
                "incidents": list(self.incidents),
            }
