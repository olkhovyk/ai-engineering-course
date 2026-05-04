from pathlib import Path
from typing import List, Tuple

import faiss
import numpy as np

from benchmarks.base import VectorDB


class FaissFlatDB(VectorDB):
    name = "faiss_flat"

    def __init__(self, index_path: Path = Path("data/indexes/faiss_flat.index")):
        self.index_path = index_path
        self.faiss_index: faiss.Index | None = None
        self.ids: list[str] = []

    def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        vectors = np.ascontiguousarray(vectors.astype("float32"))
        self.ids = ids
        self.faiss_index = faiss.IndexFlatIP(vectors.shape[1])
        self.faiss_index.add(vectors)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.faiss_index, str(self.index_path))

    def search(self, query_vec: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        if self.faiss_index is None:
            raise RuntimeError("Index is not built")
        query = np.ascontiguousarray(query_vec.reshape(1, -1).astype("float32"))
        scores, indexes = self.faiss_index.search(query, top_k)
        return [
            (self.ids[idx], float(score))
            for idx, score in zip(indexes[0], scores[0])
            if idx >= 0
        ]

    def disk_size_mb(self) -> float:
        if not self.index_path.exists():
            return 0.0
        return self.index_path.stat().st_size / (1024 * 1024)
