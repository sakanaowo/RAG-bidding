from psycopg import connect
import os


DSN = os.getenv("DATABASE_URL").replace("postgresql+psycopg", "postgresql")


SQLS = [
    "VACUUM (ANALYZE) chunks;",
    "VACUUM (ANALYZE) chunk_embeddings;",
    "REINDEX INDEX CONCURRENTLY idx_chunk_embeddings_hnsw;",
]


if __name__ == "__main__":
    with connect(DSN) as conn:
        with conn.cursor() as cur:
            for q in SQLS:
                cur.execute(q)
                print("OK:", q)
