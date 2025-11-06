# RAG Bidding System - Test Suite

This directory contains comprehensive tests for the RAG Bidding System.

## Test Structure

### Core System Tests
- **`test_core_system.py`** - Database, vector store, retrieval, and Q&A functionality
- **`test_db_connection.py`** - Basic database connectivity (legacy)

### API Tests  
- **`test_api_endpoints.py`** - Comprehensive API endpoint testing
- **`test_api_server.py`** - Test API server (bypasses upload functionality)

### Legacy Tests (for reference)
- **`test_rag_queries.py`** - Advanced RAG query testing
- **`test_quick_retrieval.py`** - Quick retrieval validation

### Test Runner
- **`run_all_tests.py`** - Orchestrates all tests in proper sequence

## Quick Start

### 1. Run Core System Tests
```bash
# Test database and core functionality
python scripts/tests/test_core_system.py
```

### 2. Start Test API Server
```bash
# Start test server (in background)
python scripts/tests/test_api_server.py &
```

### 3. Test API Endpoints
```bash
# Test all API endpoints
python scripts/tests/test_api_endpoints.py
```

### 4. Run All Tests (Recommended)
```bash
# Automated test sequence
python scripts/tests/run_all_tests.py
```

## Test Coverage

### Core System Tests ✅
- [x] PostgreSQL database connection
- [x] pgvector extension validation
- [x] LangChain PGVector integration
- [x] Vector similarity search
- [x] Retrieval system (fast/balanced modes)
- [x] Q&A chain functionality
- [x] Environment configuration

### API Endpoint Tests ✅
- [x] `/health` - Database and system health
- [x] `/stats` - System configuration and features
- [x] `/test/retrieval` - Retrieval functionality testing
- [x] `/ask` - Question answering endpoint

### Data Validation ✅
- [x] 4,512 embeddings in database
- [x] 1 collection (docs)
- [x] Document metadata structure
- [x] Multiple document types (law, bidding, etc.)

## Environment Requirements

Required environment variables:
```env
OPENAI_API_KEY=sk-proj-...
DATABASE_URL=postgresql+psycopg://sakana:sakana123@localhost:5432/rag_bidding_v2
LC_COLLECTION=docs
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o-mini
```