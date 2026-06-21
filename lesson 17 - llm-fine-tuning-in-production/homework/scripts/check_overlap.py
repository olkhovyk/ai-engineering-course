"""Check that train.jsonl has no email overlap with eval.jsonl.

The homework requires eval examples to be independent from training examples.
This script hashes normalized email text and fails if the same email appears
in both files.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TRAIN_PATH = ROOT / "data" / "train.jsonl"
EVAL_PATH = ROOT / "data" / "eval.jsonl"


def normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def hash_text(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()[:16]


def read_train_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            user_message = row["messages"][1]["content"]
            hashes[hash_text(user_message)] = f"train line {line_number}: {user_message}"
    return hashes


def read_eval_hashes(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            email = row["email"]
            hashes[hash_text(email)] = f"eval line {line_number}: {email}"
    return hashes


def main() -> None:
    train_hashes = read_train_hashes(TRAIN_PATH)
    eval_hashes = read_eval_hashes(EVAL_PATH)
    overlap = sorted(set(train_hashes) & set(eval_hashes))

    print(f"train examples: {len(train_hashes)}")
    print(f"eval examples: {len(eval_hashes)}")
    print(f"overlap: {len(overlap)}")

    if overlap:
        print()
        print("Overlapping examples:")
        for digest in overlap:
            print(f"- {digest}")
            print(f"  {train_hashes[digest]}")
            print(f"  {eval_hashes[digest]}")
        raise SystemExit(1)

    print("OK: train/eval overlap not found")


if __name__ == "__main__":
    main()
