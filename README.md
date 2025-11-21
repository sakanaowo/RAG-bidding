# 📚 RAG Bidding System

**AI-Powered Vietnamese Legal Document Retrieval & Question Answering System**

Advanced RAG system for Vietnamese bidding law documents with semantic enrichment, multi-tier caching, and BGE reranking.

---

## ⚡ Quick Start

### 1️⃣ Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/sakanaowo/RAG-bidding.git
cd RAG-bidding

# Run database setup
chmod +x setup_db.sh
./setup_db.sh

# Create environment
conda env create -f environment.yaml
conda activate rag-bidding

# Configure API keys
cp .env.example .env
nano .env  # Add OPENAI_API_KEY

# Initialize database
python scripts/bootstrap_db.py

# Import preprocessed data (4,512 enriched chunks)
python scripts/import_processed_chunks.py
```

**Time:** ~10 minutes | **See:** [Quick Setup Guide](documents/setup/QUICK_SETUP.md)

### 2️⃣ Manual Setup

**See:** [Complete Database Setup Guide](documents/setup/DATABASE_SETUP.md) for detailed instructions.

---

## 🎯 Key Features

### 🔍 Advanced Retrieval
- **Native 3072-dim embeddings** (text-embedding-3-large)
- **BGE Reranker** (Vietnamese multilingual support)
- **Semantic enrichment** with NER, concepts, keywords
- **Multi-tier caching** (Redis + PostgreSQL)
- **Adaptive retrieval** modes (fast/balanced/quality)

### 📊 Document Processing
- **Multi-file upload API** with Postman compatibility  
- **Auto-classification** (Law, Decree, Circular, Bidding documents)
- **Background processing** with real-time progress tracking
- **Hierarchical chunking** preserving legal structure
- **Entity extraction** (laws, decrees, circulars, dates)
- **TF-IDF keyword extraction** with legal term boosting

### 🗄️ Database
- **PostgreSQL 18** with pgvector extension
- **Vector search** with cosine similarity
- **JSONB metadata** for rich filtering
- **Optimized indexes** for production workloads

---

## 📊 Current System Status

| Metric | Value |
|--------|-------|
| **Documents** | 63 legal documents |
| **Chunks** | 4,512+ enriched chunks |
| **Embeddings** | 3,072 dimensions (native) |
| **Upload System** | ✅ Multi-file upload with auto-classification |
| **Database** | PostgreSQL 18 + pgvector 0.8.1 |
| **API Endpoints** | Upload, Status Tracking, Query & Search |
| **Processing Pipeline** | DOCX/PDF → Classification → Chunking → Embedding → Storage |
| **Background Tasks** | Async processing with progress tracking |

---

## 🗂️ Project Structure

```
RAG-bidding/
├── data/
│   ├── raw/                    # Raw DOCX/DOC files
│   ├── processed/              # Enriched chunks (JSONL)
│   │   ├── chunks/            # 4,512 chunks with metadata
│   │   └── metadata/          # Document metadata
│   └── outputs/               # Processing reports
├── documents/                  # 📚 Documentation
│   ├── setup/                 # Setup guides
│   ├── technical/             # Architecture & optimization
│   ├── phase-reports/         # Project milestones
│   ├── verification/          # Test reports
│   └── planning/              # Roadmaps & analysis
├── scripts/                    # 🔧 Utility scripts
│   ├── batch_reprocess_all.py        # Batch processing with enrichment
│   ├── import_processed_chunks.py    # Import to database
│   ├── bootstrap_db.py              # Initialize database
│   └── test/                        # Test suite
│       ├── integration/             # E2E tests
│       ├── preprocessing/           # Document loading tests
│       ├── chunking/               # Chunking strategy tests
│       └── pipeline/               # Pipeline tests
├── src/                        # 📦 Source code
│   ├── api/                   # FastAPI endpoints
│   ├── preprocessing/         # Document processing
│   │   ├── loaders/          # DOCX/DOC/PDF loaders
│   │   ├── parsers/          # Document parsers
│   │   └── enrichment/       # Semantic enrichment
│   ├── chunking/              # Chunking strategies
│   ├── embedding/             # Embeddings & vector store
│   ├── retrieval/             # Retrieval & reranking
│   └── generation/            # LLM generation
├── tests/                      # 🧪 Component tests
│   ├── integration/           # Multi-component tests
│   ├── retrieval/            # Search & filtering
│   └── reranking/            # Reranking models
├── .env.example               # Environment template
├── environment.yaml           # Conda environment
└── setup_db.sh               # Database setup script
```

---

## 🔑 Environment Configuration

### Essential Variables

```bash
# Database (Required)
DATABASE_URL=postgresql://rag_user:password@localhost:5432/rag_bidding_v2
LC_COLLECTION=docs

# OpenAI API (Required)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Embedding & LLM Models
EMBED_MODEL=text-embedding-3-large  # 3072 dims (native)
LLM_MODEL=gpt-4o-mini

# Retrieval Configuration
RETRIEVAL_K=5
RAG_MODE=balanced  # fast, balanced, quality
ENABLE_RERANKING=true
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
```

**Full reference:** See [.env.example](.env.example)

---

## 🚀 Usage

### Start API Server

```bash
conda activate venv  # Updated environment name
chmod +x start_server.sh
./start_server.sh
# OR manually: uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Upload New Documents (NEW!)

```bash
# Via API (Postman or curl)
curl -X POST "http://localhost:8000/upload/files" \
  -F "files=@path/to/document.docx" \
  -F "batch_name=my_batch" \
  -F "auto_classify=true"

# Check processing status
curl "http://localhost:8000/upload/status?upload_id={upload_id}"
```

### Query Documents

```bash
# Via API - Ask questions
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quy trình đấu thầu rộng rãi là gì?", "mode": "balanced"}'

# Check system stats
curl "http://localhost:8000/stats"

# Health check
curl "http://localhost:8000/health"
```

### Process Documents (Batch - Legacy)

```bash
# Add DOCX files to data/raw/
# Then run batch processing with enrichment
python scripts/batch_reprocess_all.py \
  --raw-dir data/raw \
  --output-dir data/processed

# Import to database
python scripts/import_processed_chunks.py \
  --chunks-dir data/processed/chunks
```

---

## � Documentation

### Setup Guides
- 🚀 [Quick Setup (10 min)](documents/setup/QUICK_SETUP.md)
- 📖 [Complete Database Setup](documents/setup/DATABASE_SETUP.md)
- ⚙️ [Environment Configuration](.env.example)

### Technical Documentation
- 🏗️ [Pipeline Integration Summary](documents/technical/PIPELINE_INTEGRATION_SUMMARY.md)
- ⚡ [Optimization Strategy](documents/technical/OPTIMIZATION_STRATEGY.md)
- 💾 [Cache & HNSW Explained](documents/technical/CACHE_AND_HNSW_EXPLAINED.md)

### Development
- 🗺️ [Roadmap](documents/planning/preprocess-plan/ROADMAP.md)
- 📊 [Architecture](documents/planning/preprocess-plan/PREPROCESSING_ARCHITECTURE.md)
- 🧪 [Test Suite](scripts/test/README.md)

---

## 🛠️ Technology Stack

| Category | Technology |
|----------|-----------|
| **Language** | Python 3.10 |
| **Framework** | FastAPI, LangChain 0.3.x |
| **Database** | PostgreSQL 18 + pgvector |
| **Embeddings** | OpenAI text-embedding-3-large (3072d) |
| **LLM** | GPT-4o-mini |
| **Reranker** | BGE-reranker-v2-m3 (Vietnamese) |
| **NLP** | spaCy, sentence-transformers |
| **Caching** | Redis (optional), PostgreSQL |

---

## 🧪 Testing

```bash
# Run all tests
python -m pytest scripts/test/ -v

# Run specific category
python -m pytest scripts/test/integration/ -v
python -m pytest tests/reranking/ -v

# Run single test
python scripts/test/integration/test_e2e_pipeline.py
```

**See:** [Test Suite Documentation](scripts/test/README.md)

---

## 📈 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| **Document Processing** | ~0.35s/file | With enrichment |
| **Chunk Import** | ~20 chunks/s | 3072-dim embeddings |
| **Vector Search** | ~50ms | Native cosine similarity |
| **With Reranking** | ~200ms | BGE-reranker-v2-m3 |
| **Full Pipeline** | ~250ms | Retrieval + Rerank + Generation |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 Support

- **Setup Issues:** Check [Troubleshooting Guide](documents/setup/DATABASE_SETUP.md#-troubleshooting)
- **Documentation:** Browse [documents/](documents/) folder
- **GitHub Issues:** Report bugs or request features
- **Quick Help:** See [Quick Setup Guide](documents/setup/QUICK_SETUP.md)

---

**Version:** 2.0.0  
**Last Updated:** November 4, 2025  
**Status:** ✅ Production Ready
