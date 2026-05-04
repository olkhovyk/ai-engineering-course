from abc import ABC, abstractmethod
from typing import List, Tuple

import numpy as np


class VectorDB(ABC):
    """Shared interface for FAISS, Qdrant, Chroma, and pgvector."""

    name: str

    @abstractmethod
    def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        """Build an index from float32 normalized vectors."""

    @abstractmethod
    def search(self, query_vec: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return [(doc_id, score), ...] for the nearest vectors."""

    @abstractmethod
    def disk_size_mb(self) -> float:
        """Return index storage size in MB."""

    def cleanup(self) -> None:
        """Close connections or remove temporary resources."""
        pass
