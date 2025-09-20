-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;


-- Nguồn tài liệu (file, url...)
CREATE TABLE IF NOT EXISTS documents (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
source_id TEXT NOT NULL, -- path hoặc URL duy nhất
source_type TEXT NOT NULL DEFAULT 'file', -- file|url|db|api
mime_type TEXT,
meta JSONB DEFAULT '{}'::jsonb,
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
UNIQUE (source_id, source_type)
);


-- Mỗi chunk của tài liệu
CREATE TABLE IF NOT EXISTS chunks (
id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
ord INT NOT NULL, -- thứ tự chunk trong doc
text TEXT NOT NULL,
meta JSONB DEFAULT '{}'::jsonb,
created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
UNIQUE (document_id, ord)
);


-- Vector embedding cho mỗi chunk
-- Điều chỉnh dimension theo ENV EMBEDDING_DIM
CREATE TABLE IF NOT EXISTS chunk_embeddings (
chunk_id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
embedding vector(1536) NOT NULL
);


-- Chỉ mục vector (HNSW phù hợp cho truy vấn ANN thời gian thực)
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_hnsw
ON chunk_embeddings USING hnsw (embedding vector_l2_ops);


-- Views tiện lợi
CREATE OR REPLACE VIEW v_chunk_full AS
SELECT c.id AS chunk_id, c.ord, c.text, c.meta,
d.id AS document_id, d.source_id, d.source_type, d.mime_type, d.meta AS doc_meta
FROM chunks c
JOIN documents d ON d.id = c.document_id;