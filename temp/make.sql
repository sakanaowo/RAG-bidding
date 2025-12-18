-- ========================================
-- RAG Bidding System - Schema v6.0
-- Simplified Production Ready Schema
-- Total Tables: 10 (removed collections system)
-- ========================================

BEGIN;

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 2. USER MANAGEMENT
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id);

-- 3. DOCUMENT MANAGEMENT (SIMPLIFIED)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- File info
    document_id VARCHAR(255) UNIQUE,
    document_name VARCHAR(500),
    filename VARCHAR(255),
    filepath VARCHAR(500),
    source_file TEXT,
    
    -- Classification (SIMPLIFIED - no collections needed)
    category VARCHAR(100) NOT NULL DEFAULT 'Khác', -- "Hồ sơ mời thầu", "Mẫu báo cáo", etc.
    document_type VARCHAR(50), 
    
    -- Upload info
    uploaded_by UUID REFERENCES users(id),
    file_hash VARCHAR(64),
    file_size_bytes BIGINT,
    
    -- Content stats
    total_chunks INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document indexes (optimized for category filtering)
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_documents_uploader ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id VARCHAR(255) UNIQUE NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(500),
    hierarchy_path TEXT[],
    keywords TEXT[],
    concepts TEXT[],
    entities JSONB,
    char_count INTEGER,
    has_table BOOLEAN DEFAULT false,
    has_list BOOLEAN DEFAULT false,
    is_complete_unit BOOLEAN DEFAULT true,
    retrieval_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_fts ON document_chunks USING GIN(to_tsvector('english', content));

-- Collections system removed in v6 for simplicity
-- Use documents.category for filtering instead

-- 4. VECTOR STORAGE (ENHANCED)
-- Enhance existing langchain table or create if not exists
-- NOTE: LangChain PGVector requires column name "id" (not "uuid")
CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text, -- LangChain uses "id" not "uuid"
    collection_id UUID, -- FK to langchain_pg_collection
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small (1536-dim for HNSW support)
    document TEXT, -- Chunk content
    cmetadata JSONB, -- Rich metadata from current system
    chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create HNSW vector index for fast similarity search (supports up to 2000 dimensions)
-- Using 1536-dim embeddings (text-embedding-3-small) for HNSW compatibility
-- HNSW is faster than IVFFlat for this dimension range
CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_vector 
ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64); -- Optimized for 8K-10K vectors

-- 5. CONVERSATION & LOGGING
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    summary TEXT,
    rag_mode VARCHAR(50) DEFAULT 'balanced',
    category_filter TEXT[], -- Which categories to search: ["Hồ sơ mời thầu", "Luật chính"]
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    processing_time_ms INTEGER,
    tokens_total INTEGER,
    feedback_rating INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id),
    chunk_id UUID NOT NULL REFERENCES document_chunks(id),
    citation_number INTEGER NOT NULL,
    citation_text TEXT,
    relevance_score DECIMAL(5,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),
    
    -- Query info
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64),
    rag_mode VARCHAR(50),
    
    -- Filtering context (category-based)
    categories_searched TEXT[], -- Which categories were included in search
    
    -- Performance metrics
    retrieval_count INTEGER,
    total_latency_ms INTEGER,
    
    -- Cost tracking
    tokens_total INTEGER,
    estimated_cost_usd DECIMAL(10,6),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50),
    rating INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    date DATE NOT NULL,
    total_queries INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Usage patterns (category-based)
    categories_accessed TEXT[], -- Which categories accessed: ["Hồ sơ mời thầu", "Luật chính"]
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT user_usage_metrics_unique UNIQUE (user_id, date)
);

-- 6. TRIGGERS & FUNCTIONS
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. DATA MIGRATION (Category Assignment)
-- Update existing documents with categories based on current data patterns
UPDATE documents SET category = 
    CASE 
        WHEN filepath LIKE '%Ho so moi thau%' OR document_name LIKE '%Hồ sơ%' THEN 'Hồ sơ mời thầu'
        WHEN filepath LIKE '%Mau bao cao%' OR document_name LIKE '%báo cáo%' THEN 'Mẫu báo cáo'  
        WHEN filepath LIKE '%Cau hoi thi%' OR document_name LIKE '%câu hỏi%' THEN 'Câu hỏi thi'
        WHEN filepath LIKE '%Luat chinh%' OR document_type = 'law' THEN 'Luật chính'
        WHEN document_type IN ('decree', 'circular') OR filepath LIKE '%Nghi dinh%' OR filepath LIKE '%Thong tu%' OR filepath LIKE '%Quyet dinh%' THEN 'Quy định khác'
        ELSE 'Khác'
    END
WHERE category IS NULL OR category = 'Khác';

COMMIT;

DO $$
BEGIN
    RAISE NOTICE '🎉 Schema v6.0 setup completed successfully!';
    RAISE NOTICE '📊 Total tables: 10 (simplified from v5)';
    RAISE NOTICE '✅ Collections system removed - using category-based filtering';
    RAISE NOTICE '🚀 Ready for production use!';
END$$;