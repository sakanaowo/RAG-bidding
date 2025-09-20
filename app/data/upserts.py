from typing import List, Tuple
from sqlalchemy import text
from app.core.db import SessionLocal

SQL_UPSERT_DOC = text(
    """
    INSERT INTO documents (source_id, source_type, mime_type, meta)
    VALUES (:source_id, :source_type, :mime_type, COALESCE(:meta, '{}'::jsonb))
        ON CONFLICT (source_id, source_type) DO UPDATE
            SET mime_type=EXCLUDED.mime_type,
                meta = documents.meta || EXCLUDED.meta,
                updated_at=now()
    RETURNING id;
    """
)

SQL_INSERT_CHUNK = text(
    """
    INSERT INTO chunks (document_id, ord, text, meta)
    VALUES (:document_id, :ord, :text, COALESCE(:meta, '{}'::jsonb))
    RETURNING id;
    """
)

SQL_UPSERT_EMB = text(
    """
    INSERT INTO chunk_embeddings (chunk_id, embedding)
    VALUES (:chunk_id, :embedding)
    ON CONFLICT (chunk_id) DO UPDATE SET embedding=EXCLUDED.embedding;
    """
)


def upsert_document_with_chunks(
    source_id: str,
    source_type: str,
    mime_type: str,
    chunks: List[Tuple[int, str]],
    embeddings: List[List[float]],
):
    assert len(chunks) == len(
        embeddings
    ), "Chunks and embeddings must have the same length"
    with SessionLocal() as s, s.begin():
        doc_id = s.execute(
            SQL_UPSERT_DOC,
            {
                "source_id": source_id,
                "source_type": source_type,
                "mime_type": mime_type,
                "meta": None,
            },
        ).scalar_one()
        for (ord_, text_), emb in zip(chunks, embeddings):
            chunk_id = s.execute(
                SQL_INSERT_CHUNK,
                {"document_id": doc_id, "ord": ord_, "text": text_, "meta": None},
            ).scalar_one()
            s.execute(SQL_UPSERT_EMB, {"chunk_id": chunk_id, "embedding": emb})
