import shutil
from pathlib import Path
from typing import List, Tuple

import chromadb
import numpy as np

from benchmarks.base import VectorDB


class ChromaDB(VectorDB):
    name = "chroma"

    def __init__(
        self,
        persist_dir: Path = Path("data/indexes/chroma"),
        collection_name: str = "quora_benchmark",
        batch_size: int = 2048,
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.batch_size = batch_size
        self.client = None
        self.collection = None

    def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        if self.persist_dir.exists():
            shutil.rmtree(self.persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        for start in range(0, len(ids), self.batch_size):
            end = min(start + self.batch_size, len(ids))
            batch_ids = ids[start:end]
            self.collection.add(
                ids=batch_ids,
                embeddings=vectors[start:end].astype("float32").tolist(),
            )

    def search(self, query_vec: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        if self.collection is None:
            raise RuntimeError("Index is not built")
        result = self.collection.query(
            query_embeddings=[query_vec.astype("float32").tolist()],
            n_results=top_k,
        )
        ids = result["ids"][0]
        distances = result["distances"][0]
        return [(str(doc_id), float(1.0 - distance)) for doc_id, distance in zip(ids, distances)]

    def disk_size_mb(self) -> float:
        if not self.persist_dir.exists():
            return 0.0
        return sum(p.stat().st_size for p in self.persist_dir.rglob("*") if p.is_file()) / (
            1024 * 1024
        )
