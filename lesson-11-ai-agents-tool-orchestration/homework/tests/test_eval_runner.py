import csv
from pathlib import Path

import pytest

from src.eval_runner import evaluate_case, run_eval
from src.finance_data import Transaction
from datetime import datetime


def tx(date, merchant, amount, category, account="main_debit", recurring=False):
    return Transaction(
        date=datetime.fromisoformat(date),
        merchant=merchant,
        amount=amount,
        currency="USD",
        category=category,
        account=account,
        recurring=recurring,
    )


def test_evaluate_case_marks_intent_and_tool_accuracy():
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.0, "coffee"),
        tx("2025-06-02T08:00", "Blue Bottle", -6.0, "coffee"),
    ]
    case = {
        "id": "coffee",
        "question": "Скільки витратив на каву?",
        "expected_intent": "category_spending",
        "expected_tools": ["spending_for_category"],
    }

    row = evaluate_case("baseline", case, transactions)

    assert row["architecture"] == "baseline"
    assert row["case_id"] == "coffee"
    assert row["intent"] == "category_spending"
    assert row["intent_ok"] == "true"
    assert row["tool_ok"] == "true"
    assert row["tool_calls"] == "spending_for_category"
    assert float(row["latency_ms"]) >= 0


def test_run_eval_writes_rows_for_baseline_and_crew():
    pytest.importorskip("langgraph")
    test_output_dir = Path("results")
    test_output_dir.mkdir(exist_ok=True)
    golden_path = test_output_dir / "test_golden_set.json"
    output_path = test_output_dir / "test_eval_results.csv"
    golden_path.write_text(
        """
        [
          {
            "id": "coffee",
            "question": "Скільки витратив на каву?",
            "expected_intent": "category_spending",
            "expected_tools": ["spending_for_category"]
          }
        ]
        """,
        encoding="utf-8",
    )
    transactions = [
        tx("2025-06-01T08:00", "Aroma Kava", -4.0, "coffee"),
        tx("2025-06-02T08:00", "Blue Bottle", -6.0, "coffee"),
    ]

    rows = run_eval(
        transactions=transactions,
        golden_path=golden_path,
        output_path=output_path,
        architectures=["baseline", "crew"],
    )

    assert len(rows) == 2
    with output_path.open("r", encoding="utf-8", newline="") as file:
        saved_rows = list(csv.DictReader(file))

    assert [row["architecture"] for row in saved_rows] == ["baseline", "crew"]
    assert saved_rows[0]["intent_ok"] == "true"
