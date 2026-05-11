from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.config import get_settings
from app.rag import index_source_document


def main() -> None:
    settings = get_settings()
    source_path = ROOT_DIR / "data" / "source.md"
    result = index_source_document(source_path, settings)

    print("Indexed source document")
    print(f"  source: {result['source_path']}")
    print(f"  collection: {result['collection']}")
    print(f"  chunks: {result['chunks']}")
    print(f"  vector size: {result['vector_size']}")


if __name__ == "__main__":
    main()
