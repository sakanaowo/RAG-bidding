-- ========================================
-- RAG Bidding System - Schema v5.0 
-- Production Ready Database Schema
-- ========================================
-- Date: November 28, 2025
-- Total Tables: 12 (from 3 current)
-- Estimated Execution: 5-10 minutes
-- ========================================

BEGIN;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ========================================
-- 1. USER MANAGEMENT
-- ========================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255), -- NULL for OAuth users
    
    -- Profile
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user', -- user, admin, manager
    
    -- OAuth
    oauth_provider VARCHAR(50), -- google, microsoft
    oauth_id VARCHAR(255),
    
    -- Settings (flexible preferences in JSONB)
    preferences JSONB DEFAULT '{}', -- UI settings, default collections, etc.
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP -- Soft delete
);

-- User indexes
CREATE INDEX idx_users_role ON users(role) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id) WHERE oauth_provider IS NOT NULL;
CREATE INDEX idx_users_active ON users(is_active) WHERE deleted_at IS NULL;

-- ========================================
-- 2. DOCUMENT MANAGEMENT (Enhanced)
-- ========================================

-- Enhanced documents table (keep existing + add new fields)
ALTER TABLE documents ADD COLUMN IF NOT EXISTS uploaded_by UUID REFERENCES users(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;

-- Add new indexes for enhanced documents
CREATE INDEX IF NOT EXISTS idx_documents_uploader ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash) WHERE file_hash IS NOT NULL;

-- Document chunks table (extracted from langchain metadata)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id VARCHAR(255) UNIQUE NOT NULL, -- From cmetadata->>'chunk_id'
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Content (from langchain_pg_embedding.document)
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL, -- From cmetadata->>'chunk_index'
    
    -- Structure (from cmetadata analysis)
    section_title VARCHAR(500), -- From cmetadata->>'section_title'
    hierarchy_path TEXT[], -- From cmetadata->'hierarchy' array
    
    -- Enrichment (from cmetadata->>'extra_metadata')
    keywords TEXT[], -- From extra_metadata->'keywords'
    concepts TEXT[], -- From extra_metadata->'concepts'  
    entities JSONB, -- From extra_metadata->'entities'
    
    -- Content analysis (from cmetadata)
    char_count INTEGER, -- From cmetadata->>'char_count'
    has_table BOOLEAN DEFAULT false, -- From cmetadata->>'has_table'
    has_list BOOLEAN DEFAULT false, -- From cmetadata->>'has_list'
    is_complete_unit BOOLEAN DEFAULT true, -- From cmetadata->>'is_complete_unit'
    
    -- Usage analytics
    retrieval_count INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document chunks indexes
CREATE INDEX idx_document_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_document_chunks_index ON document_chunks(document_id, chunk_index);
CREATE INDEX idx_document_chunks_keywords ON document_chunks USING GIN(keywords);
CREATE INDEX idx_document_chunks_section ON document_chunks(section_title);
CREATE INDEX idx_document_chunks_fts ON document_chunks USING GIN(to_tsvector('english', content));

-- Document collections table
CREATE TABLE document_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE, -- NULL for system collections
    
    -- Collection info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    collection_type VARCHAR(50) DEFAULT 'manual', -- manual, smart, system
    
    -- Smart filtering (based on current data patterns)
    document_types TEXT[], -- Filter by: law, decree, circular, bidding_form, etc.
    categories TEXT[], -- Filter by: legal, bidding, etc.
    
    -- Sharing
    is_public BOOLEAN DEFAULT false,
    
    -- Stats (updated by triggers)
    document_count INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT document_collections_owner_name_unique UNIQUE (owner_id, name)
);

-- Collection indexes
CREATE INDEX idx_document_collections_owner ON document_collections(owner_id);
CREATE INDEX idx_document_collections_type ON document_collections(collection_type);
CREATE INDEX idx_document_collections_public ON document_collections(is_public) WHERE is_public = true;
CREATE INDEX idx_document_collections_doc_types ON document_collections USING GIN(document_types);

-- Collection documents junction table
CREATE TABLE collection_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- M:N relationship
    collection_id UUID NOT NULL REFERENCES document_collections(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    
    -- Metadata
    added_by UUID REFERENCES users(id), -- Who added this document
    display_order INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT collection_documents_unique UNIQUE (collection_id, document_id)
);

-- Collection documents indexes
CREATE INDEX idx_collection_documents_collection ON collection_documents(collection_id, display_order);
CREATE INDEX idx_collection_documents_document ON collection_documents(document_id);

-- ========================================
-- 3. VECTOR STORAGE (Simplified)
-- ========================================

-- Enhance existing langchain_pg_embedding table
ALTER TABLE langchain_pg_embedding 
ADD COLUMN IF NOT EXISTS chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL;

-- Remove collection_id dependency (if exists)
-- ALTER TABLE langchain_pg_embedding DROP COLUMN IF EXISTS collection_id;

-- Add indexes for enhanced embedding table
CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_chunk ON langchain_pg_embedding(chunk_id);

-- Ensure vector index exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'langchain_pg_embedding' 
        AND indexname LIKE '%vector%'
    ) THEN
        CREATE INDEX idx_langchain_pg_embedding_vector 
        ON langchain_pg_embedding 
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
    END IF;
END$$;

-- ========================================
-- 4. CONVERSATION MANAGEMENT
-- ========================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Content
    title VARCHAR(500),
    summary TEXT,
    
    -- RAG configuration
    rag_mode VARCHAR(50) DEFAULT 'balanced', -- fast, balanced, quality
    collection_filter JSONB, -- Which collections to search: {"collection_ids": [...], "document_types": [...]}
    
    -- Stats
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Conversation indexes
CREATE INDEX idx_conversations_user ON conversations(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_conversations_last_message ON conversations(user_id, last_message_at DESC);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Content
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    
    -- Sources (for assistant messages)
    sources JSONB, -- Array of source references
    
    -- Performance metrics
    processing_time_ms INTEGER,
    tokens_prompt INTEGER,
    tokens_completion INTEGER,
    tokens_total INTEGER,
    
    -- Caching
    cache_hit BOOLEAN DEFAULT false,
    
    -- Inline feedback
    feedback_rating INTEGER CHECK (feedback_rating >= 1 AND feedback_rating <= 5),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Message indexes
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_feedback ON messages(feedback_rating) WHERE feedback_rating IS NOT NULL;

CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id),
    chunk_id UUID NOT NULL REFERENCES document_chunks(id),
    
    -- Citation info
    citation_number INTEGER NOT NULL, -- [1], [2], [3]
    citation_text TEXT, -- Snippet shown to user
    
    -- Relevance scores
    relevance_score DECIMAL(5,4), -- Initial vector similarity
    rerank_score DECIMAL(5,4), -- BGE reranker score
    
    -- User interaction
    clicked BOOLEAN DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Citation indexes
CREATE INDEX idx_citations_message ON citations(message_id, citation_number);
CREATE INDEX idx_citations_document ON citations(document_id);
CREATE INDEX idx_citations_chunk ON citations(chunk_id);

-- ========================================
-- 5. ANALYTICS & LOGGING
-- ========================================

CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    message_id UUID REFERENCES messages(id),
    
    -- Query info
    query_text TEXT NOT NULL,
    query_hash VARCHAR(64) NOT NULL, -- For deduplication
    rag_mode VARCHAR(50),
    
    -- Filtering context (based on current data)
    collection_ids UUID[], -- Which collections were searched
    document_types TEXT[], -- Which document types were included
    
    -- Performance metrics
    retrieval_count INTEGER, -- Number of chunks retrieved
    rerank_count INTEGER, -- Number of chunks reranked
    total_latency_ms INTEGER,
    
    -- Caching
    cache_hit BOOLEAN DEFAULT false,
    
    -- Cost tracking
    tokens_total INTEGER,
    estimated_cost_usd DECIMAL(10,6),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query indexes
CREATE INDEX idx_queries_user ON queries(user_id, created_at DESC);
CREATE INDEX idx_queries_conversation ON queries(conversation_id);
CREATE INDEX idx_queries_hash ON queries(query_hash);
CREATE INDEX idx_queries_doc_types ON queries USING GIN(document_types);

CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Feedback content
    feedback_type VARCHAR(50) DEFAULT 'rating', -- rating, issue, suggestion
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    issues TEXT[], -- incorrect, incomplete, outdated, irrelevant
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feedback indexes
CREATE INDEX idx_feedback_user ON feedback(user_id);
CREATE INDEX idx_feedback_message ON feedback(message_id);
CREATE INDEX idx_feedback_rating ON feedback(rating) WHERE rating IS NOT NULL;

CREATE TABLE user_usage_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    -- Time dimension
    date DATE NOT NULL,
    
    -- Usage metrics
    total_queries INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    
    -- Usage patterns (based on current data types)
    collections_used UUID[], -- Which collections accessed
    document_types_accessed TEXT[], -- law, decree, circular, bidding_form, etc.
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT user_usage_metrics_unique UNIQUE (user_id, date)
);

-- Usage metrics indexes
CREATE INDEX idx_user_usage_metrics_user_date ON user_usage_metrics(user_id, date DESC);
CREATE INDEX idx_user_usage_metrics_date ON user_usage_metrics(date DESC);

-- ========================================
-- 6. DATA MIGRATION & INITIAL DATA
-- ========================================

-- Migrate document chunks from existing langchain embeddings
INSERT INTO document_chunks (
    chunk_id, document_id, content, chunk_index,
    section_title, hierarchy_path, keywords, concepts,
    char_count, has_table, has_list, is_complete_unit,
    created_at
)
SELECT 
    e.cmetadata->>'chunk_id' as chunk_id,
    d.id as document_id,
    e.document as content,
    COALESCE((e.cmetadata->>'chunk_index')::INTEGER, 0) as chunk_index,
    e.cmetadata->>'section_title' as section_title,
    CASE 
        WHEN e.cmetadata->'hierarchy' IS NOT NULL 
        THEN ARRAY(SELECT jsonb_array_elements_text(e.cmetadata->'hierarchy'))
        ELSE NULL 
    END as hierarchy_path,
    CASE 
        WHEN e.cmetadata->'extra_metadata'->'keywords' IS NOT NULL
        THEN ARRAY(SELECT jsonb_array_elements_text(e.cmetadata->'extra_metadata'->'keywords'))
        ELSE NULL 
    END as keywords,
    CASE 
        WHEN e.cmetadata->'extra_metadata'->'concepts' IS NOT NULL
        THEN ARRAY(SELECT jsonb_array_elements_text(e.cmetadata->'extra_metadata'->'concepts'))
        ELSE NULL 
    END as concepts,
    COALESCE((e.cmetadata->>'char_count')::INTEGER, LENGTH(e.document)) as char_count,
    COALESCE((e.cmetadata->>'has_table')::BOOLEAN, false) as has_table,
    COALESCE((e.cmetadata->>'has_list')::BOOLEAN, false) as has_list,
    COALESCE((e.cmetadata->>'is_complete_unit')::BOOLEAN, true) as is_complete_unit,
    COALESCE(e.created_at, CURRENT_TIMESTAMP) as created_at
FROM langchain_pg_embedding e
JOIN documents d ON d.document_id = e.cmetadata->>'document_id'
WHERE e.cmetadata->>'chunk_id' IS NOT NULL
ON CONFLICT (chunk_id) DO NOTHING;

-- Link embeddings to chunks
UPDATE langchain_pg_embedding 
SET chunk_id = dc.id
FROM document_chunks dc 
WHERE langchain_pg_embedding.cmetadata->>'chunk_id' = dc.chunk_id
AND langchain_pg_embedding.chunk_id IS NULL;

-- Create default system collections
INSERT INTO document_collections (owner_id, name, description, collection_type, document_types, is_public) VALUES 
(NULL, 'Luật và Nghị định', 'Văn bản pháp luật: Luật, Nghị định, Thông tư', 'system', ARRAY['law', 'decree', 'circular'], true),
(NULL, 'Hồ sơ đấu thầu', 'Các mẫu biểu và hướng dẫn đấu thầu', 'system', ARRAY['bidding_form', 'bidding'], true),
(NULL, 'Mẫu báo cáo', 'Các mẫu báo cáo và biểu mẫu', 'system', ARRAY['report_template'], true),
(NULL, 'Câu hỏi thi', 'Các câu hỏi và đề thi mẫu', 'system', ARRAY['exam_question'], true);

-- Populate collection_documents for system collections
INSERT INTO collection_documents (collection_id, document_id, added_by, display_order)
SELECT 
    c.id as collection_id,
    d.id as document_id,
    NULL as added_by,
    ROW_NUMBER() OVER (PARTITION BY c.id ORDER BY d.created_at) as display_order
FROM document_collections c
CROSS JOIN documents d 
WHERE d.document_type = ANY(c.document_types)
AND c.collection_type = 'system'
ON CONFLICT (collection_id, document_id) DO NOTHING;

-- Update collection stats
UPDATE document_collections 
SET 
    document_count = (
        SELECT COUNT(*) FROM collection_documents cd 
        WHERE cd.collection_id = document_collections.id
    ),
    total_chunks = (
        SELECT SUM(d.total_chunks) 
        FROM collection_documents cd 
        JOIN documents d ON d.id = cd.document_id
        WHERE cd.collection_id = document_collections.id
    )
WHERE collection_type = 'system';

-- ========================================
-- 7. TRIGGERS & FUNCTIONS
-- ========================================

-- Function to update collection stats
CREATE OR REPLACE FUNCTION update_collection_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE document_collections 
        SET 
            document_count = document_count + 1,
            total_chunks = total_chunks + COALESCE((SELECT total_chunks FROM documents WHERE id = NEW.document_id), 0)
        WHERE id = NEW.collection_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE document_collections 
        SET 
            document_count = document_count - 1,
            total_chunks = total_chunks - COALESCE((SELECT total_chunks FROM documents WHERE id = OLD.document_id), 0)
        WHERE id = OLD.collection_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger for collection stats
DROP TRIGGER IF EXISTS trigger_update_collection_stats ON collection_documents;
CREATE TRIGGER trigger_update_collection_stats
    AFTER INSERT OR DELETE ON collection_documents
    FOR EACH ROW EXECUTE FUNCTION update_collection_stats();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at triggers to tables that need them
CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_document_chunks_updated_at BEFORE UPDATE ON document_chunks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_document_collections_updated_at BEFORE UPDATE ON document_collections FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 8. PERMISSIONS & SECURITY
-- ========================================

-- Create application role if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rag_app') THEN
        CREATE ROLE rag_app WITH LOGIN PASSWORD 'your_secure_password_here';
    END IF;
END$$;

-- Grant permissions
GRANT USAGE ON SCHEMA public TO rag_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO rag_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO rag_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rag_app;

-- ========================================
-- COMMIT TRANSACTION
-- ========================================

COMMIT;

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Verify table creation
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Verify data migration
SELECT 
    'documents' as table_name, COUNT(*) as row_count FROM documents
UNION ALL
SELECT 
    'document_chunks' as table_name, COUNT(*) as row_count FROM document_chunks
UNION ALL
SELECT 
    'document_collections' as table_name, COUNT(*) as row_count FROM document_collections
UNION ALL
SELECT 
    'collection_documents' as table_name, COUNT(*) as row_count FROM collection_documents
UNION ALL
SELECT 
    'langchain_pg_embedding' as table_name, COUNT(*) as row_count FROM langchain_pg_embedding;

-- Verify collection stats
SELECT 
    name,
    collection_type,
    document_count,
    total_chunks,
    array_length(document_types, 1) as type_count
FROM document_collections 
ORDER BY collection_type, name;

PRINT '🎉 Schema v5.0 migration completed successfully!';
PRINT 'Total tables: 12';
PRINT 'Ready for production use.';