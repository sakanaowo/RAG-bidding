-- Simple Documents Table for Bidding Legal Documents
-- Created: 2025-11-19
-- Purpose: Manage 70 documents across 7 categories

CREATE TABLE IF NOT EXISTS documents (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Unique Document Identifier
    document_id VARCHAR(255) UNIQUE NOT NULL,
    -- Examples: "LUA-90-2025-QH15", "ND-214-2025-CP", "FORM-HSYC-XAYLAP"
    
    -- Document Info
    document_name TEXT NOT NULL,
    -- "Luật số 90/2025/QH15 về sửa đổi Luật Đấu thầu"
    
    -- Classification (7 categories)
    category VARCHAR(100) NOT NULL,
    -- "Luật chính", "Nghị định", "Thông tư", "Quyết định",
    -- "Hồ sơ mời thầu", "Mẫu báo cáo", "Câu hỏi thi"
    
    document_type VARCHAR(50) NOT NULL,
    -- "law", "decree", "circular", "decision", 
    -- "bidding_form", "report_template", "exam_question"
    
    -- File Information
    source_file TEXT NOT NULL,
    -- "data/raw/Luat chinh/Luat so 90 2025-qh15.docx"
    
    file_name TEXT NOT NULL,
    -- "Luat so 90 2025-qh15.docx"
    
    -- Processing Status
    total_chunks INTEGER DEFAULT 0,
    
    status VARCHAR(50) DEFAULT 'active',
    -- "active", "inactive", "archived"
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX idx_documents_category ON documents(category);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_source ON documents(source_file);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_documents_updated_at();

-- Comments
COMMENT ON TABLE documents IS 'Master table for all legal documents related to bidding';
COMMENT ON COLUMN documents.document_id IS 'Unique identifier following Vietnamese legal citation format';
COMMENT ON COLUMN documents.category IS 'One of 7 categories mapping to data/raw folders';
COMMENT ON COLUMN documents.status IS 'Document status for toggle functionality';
