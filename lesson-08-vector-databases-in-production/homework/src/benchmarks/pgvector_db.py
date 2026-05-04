from typing import List, Tuple

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from benchmarks.base import VectorDB


class PgVectorDB(VectorDB):
    name = "pgvector"

    def __init__(
        self,
        dsn: str = "postgresql://bench:bench@localhost:5432/bench",
        table_name: str = "quora_vectors",
        m: int = 32,
        ef_construction: int = 200,
    ):
        self.dsn = dsn
        self.table_name = table_name
        self.m = m
        self.ef_construction = ef_construction
        self.conn = psycopg.connect(self.dsn)
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self.conn.commit()
        register_vector(self.conn)

    def index(self, vectors: np.ndarray, ids: List[str]) -> None:
        dim = int(vectors.shape[1])
        with self.conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            cur.execute(
                f"""
                CREATE TABLE {self.table_name} (
                    id TEXT PRIMARY KEY,
                    embedding VECTOR({dim})
                )
                """
            )
            rows = [(doc_id, vector.astype("float32")) for doc_id, vector in zip(ids, vectors)]
            cur.executemany(
                f"INSERT INTO {self.table_name} (id, embedding) VALUES (%s, %s)",
                rows,
            )
            cur.execute(
                f"""
                CREATE INDEX {self.table_name}_hnsw_idx
                ON {self.table_name}
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = {self.m}, ef_construction = {self.ef_construction})
                """
            )
        self.conn.commit()

    def search(self, query_vec: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        query = query_vec.astype("float32")
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, 1 - (embedding <=> %s) AS score
                FROM {self.table_name}
                ORDER BY embedding <=> %s
                LIMIT %s
                """,
                (query, query, top_k),
            )
            return [(str(row[0]), float(row[1])) for row in cur.fetchall()]

    def disk_size_mb(self) -> float:
        with self.conn.cursor() as cur:
            cur.execute("SELECT pg_total_relation_size(%s)", (self.table_name,))
            bytes_size = cur.fetchone()[0] or 0
        return bytes_size / (1024 * 1024)

    def cleanup(self) -> None:
        self.conn.close()
