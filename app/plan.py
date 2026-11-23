import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "bcc_deposits.json").read_text(encoding="utf-8"))
DEPOSITS = {d["id"]: d for d in DATA["deposits"]}
HORIZON = 12


def interest(amount, rate, months):
    return round(amount * ((1 + rate / 100 / 12) ** months - 1))


def _goal_term(months):
    fitting = [t for t in DEPOSITS["my_goal"]["terms"] if t <= months]
    return max(fitting) if fitting else None


def build_plan(total, emergency=0, goals=None, topup=False):
    goals = goals or []
    total = int(total)
    emergency = max(0, min(int(emergency), total))
    rest = total - emergency
    items = []

    if emergency:
        d = DEPOSITS["champion"]
        items.append({
            "deposit": d["id"], "name": d["name"], "amount": emergency, "term": 13,
            "rate": d["rate_min"], "why": "можно снимать в любой момент",
            "months": HORIZON, "income": interest(emergency, d["rate_min"], HORIZON),
        })

    for g in sorted(goals, key=lambda x: x["months"]):
        amount = max(0, min(int(g["amount"]), rest))
        if not amount:
            continue
        term = _goal_term(int(g["months"]))
        if term:
            d = DEPOSITS["my_goal"]
            items.append({
                "deposit": d["id"], "name": d["name"], "amount": amount, "term": term,
                "rate": d["rate_min"], "why": f"{g.get('label') or 'цель'} через {g['months']} мес.",
                "months": term, "income": interest(amount, d["rate_min"], term),
            })
        else:
            d = DEPOSITS["champion"]
            items.append({
                "deposit": d["id"], "name": d["name"], "amount": amount, "term": 13,
                "rate": d["rate_min"], "why": f"{g.get('label') or 'цель'} раньше 3 мес. — нужен доступ",
                "months": int(g["months"]), "income": interest(amount, d["rate_min"], int(g["months"])),
            })
        rest -= amount

    if rest > 0:
        d = DEPOSITS["my_goal"]
        items.append({
            "deposit": d["id"], "name": d["name"], "amount": rest, "term": 12,
            "rate": d["rate_min"], "why": "не понадобятся год — максимальная ставка" + (", можно пополнять" if topup else ""),
            "months": HORIZON, "income": interest(rest, d["rate_min"], HORIZON),
        })

    income = sum(i["income"] for i in items)
    flexible_only = sum(interest(i["amount"], DEPOSITS["champion"]["rate_min"], i["months"]) for i in items)
    return {
        "items": items,
        "total": total,
        "income": income,
        "baseline_card": 0,
        "baseline_flexible": flexible_only,
        "gain_vs_flexible": income - flexible_only,
        "source": DATA["source"],
    }
