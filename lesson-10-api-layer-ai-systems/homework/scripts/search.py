from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.rag import search_chunks


def main() -> None:
    query = "Where should application config be stored?"
    chunks = search_chunks(query, top_k=3)

    print(f"Query: {query}")
    for chunk in chunks:
        print()
        print(f"{chunk['chunk_id']} score={chunk['score']:.4f}")
        print(chunk["text"][:500])


if __name__ == "__main__":
    main()

