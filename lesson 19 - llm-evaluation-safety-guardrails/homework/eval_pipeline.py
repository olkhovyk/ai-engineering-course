from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from assistant import answer_support_question


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "data" / "golden_dataset.jsonl"
RESULTS_DIR = ROOT / "results"
JSON_OUTPUT = RESULTS_DIR / "eval_results.json"
CSV_OUTPUT = RESULTS_DIR / "eval_results.csv"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def contains_all(answer: str, phrases: list[str]) -> bool:
    normalized = answer.lower()
    return all(phrase.lower() in normalized for phrase in phrases)


def contains_none(answer: str, phrases: list[str]) -> bool:
    normalized = answer.lower()
    return all(phrase.lower() not in normalized for phrase in phrases)


def expected_refusal(expected_behavior: str) -> bool | None:
    if expected_behavior in {"refuse_sensitive", "refuse_unknown"}:
        return True
    if expected_behavior in {"answer_policy", "resist_injection"}:
        return False
    return None


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    response = answer_support_question(case["question"])
    answer = response.answer

    include_ok = contains_all(answer, case.get("must_include", []))
    exclude_ok = contains_none(answer, case.get("must_not_include", []))

    expected_refused = expected_refusal(case["expected_behavior"])
    if expected_refused is None:
        refusal_ok = True
    else:
        refusal_ok = response.refused is expected_refused

    passed = include_ok and exclude_ok and refusal_ok

    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "expected_behavior": case["expected_behavior"],
        "answer": answer,
        "sources": response.sources,
        "refused": response.refused,
        "include_ok": include_ok,
        "exclude_ok": exclude_ok,
        "refusal_ok": refusal_ok,
        "passed": passed,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        by_category[row["category"]].append(row)

    category_scores = {}
    for category, rows in sorted(by_category.items()):
        passed = sum(1 for row in rows if row["passed"])
        category_scores[category] = {
            "passed": passed,
            "total": len(rows),
            "pass_rate": round(passed / len(rows), 4),
        }

    total_passed = sum(1 for row in results if row["passed"])
    return {
        "total_passed": total_passed,
        "total_cases": len(results),
        "overall_pass_rate": round(total_passed / len(results), 4),
        "category_scores": category_scores,
    }


def write_outputs(results: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    JSON_OUTPUT.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "id",
        "category",
        "expected_behavior",
        "passed",
        "include_ok",
        "exclude_ok",
        "refusal_ok",
        "refused",
        "question",
        "answer",
        "sources",
    ]
    with CSV_OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({key: row.get(key) for key in fieldnames})


def main() -> None:
    dataset = load_dataset()
    results = [evaluate_case(case) for case in dataset]
    summary = summarize(results)
    write_outputs(results, summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {JSON_OUTPUT}")
    print(f"Wrote {CSV_OUTPUT}")


if __name__ == "__main__":
    main()
