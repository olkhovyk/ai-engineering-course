from typing import List, Tuple

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from benchmarks.base import VectorDB


class QdrantDB(VectorDB):
    name = "qdrant"

    def __init__(
        self,
        url: str = "http://localhost:6333",
        collection_name: str = "quora_benchmark",
        batch_size: int = 512,
    ):
        self.client = QdrantClient(url=url)
        self.collection_name = collection_name
        self.batch_size = batch_size

    def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        dim = int(vectors.shape[1])
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

        for start in range(0, len(ids), self.batch_size):
            end = min(start + self.batch_size, len(ids))
            points = [
                PointStruct(
                    id=idx,
                    vector=vectors[i].astype("float32").tolist(),
                    payload={"doc_id": ids[i]},
                )
                for idx, i in enumerate(range(start, end), start=start)
            ]
            self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vec: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        query = query_vec.astype("float32").tolist()
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query,
                limit=top_k,
                with_payload=True,
            )
            hits = response.points
        else:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query,
                limit=top_k,
                with_payload=True,
            )
        return [(str(hit.payload["doc_id"]), float(hit.score)) for hit in hits]

    def disk_size_mb(self) -> float:
        info = self.client.get_collection(self.collection_name)
        vectors_count = (
            getattr(info, "vectors_count", None)
            or getattr(info, "points_count", None)
            or getattr(info, "indexed_vectors_count", None)
            or 0
        )
        vector_size = info.config.params.vectors.size
        return (vectors_count * vector_size * 4) / (1024 * 1024)
