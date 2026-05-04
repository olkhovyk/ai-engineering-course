import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


def read_jsonl(path: Path) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    texts: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            ids.append(str(row["id"]))
            texts.append(str(row["text"]))
    return ids, texts


def write_ids(path: Path, ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(ids), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cached embeddings.")
    parser.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ids-output", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", default=None, help="Use 'cuda' for NVIDIA GPU or 'cpu'.")
    args = parser.parse_args()

    ids, texts = read_jsonl(args.input)
    model = SentenceTransformer(args.model, device=args.device)
    vectors = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.save(args.output, vectors)
    ids_output = args.ids_output or args.output.with_suffix(".ids.txt")
    write_ids(ids_output, ids)

    print(f"Wrote vectors: {args.output} shape={vectors.shape}")
    print(f"Wrote ids: {ids_output} count={len(ids)}")


if __name__ == "__main__":
    main()
