from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Transaction:
    date: datetime
    merchant: str
    amount: float
    currency: str
    category: str
    account: str
    recurring: bool


def load_transactions(path: str | Path) -> list[Transaction]:
    transactions: list[Transaction] = []
    with Path(path).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            transactions.append(
                Transaction(
                    date=datetime.fromisoformat(row["date"]),
                    merchant=row["merchant"],
                    amount=float(row["amount"]),
                    currency=row["currency"],
                    category=row["category"],
                    account=row["account"],
                    recurring=row["recurring"].lower() == "true",
                )
            )
    return transactions
