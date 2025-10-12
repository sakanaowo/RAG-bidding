# 📁 Project Restructure Guide

**Date**: October 12, 2025  
**Status**: ✅ Migration Completed  
**Branch**: `enhancement/1-phase1-implement`

## 🎯 Overview

Dự án RAG-bidding đã được tái cấu trúc để phù hợp với best practices và dễ dàng mở rộng theo từng phase của hệ thống RAG.

## 📊 Before vs After

### Before (Old Structure)
```
RAG-bidding/
├── app/
│   ├── api/
│   ├── core/          # Mixed configs & core logic
│   ├── data/          # Mixed processing stages
│   └── rag/           # All RAG components together
├── config/
└── scripts/
```

### After (New Structure)
```
RAG-bidding/
├── config/            # ✅ Centralized configuration
├── src/               # ✅ Source code by RAG phases
│   ├── ingestion/     # Phase 1: Data collection
│   ├── preprocessing/ # Phase 2: Text cleaning
│   ├── chunking/      # Phase 3: Document chunking
│   ├── embedding/     # Phase 4: Vector generation
│   ├── retrieval/     # Phase 5: Query & retrieval (Current focus)
│   ├── generation/    # Phase 6: Response generation
│   └── evaluation/    # Phase 7: Metrics & evaluation
├── api/               # ✅ API layer separated
├── tests/             # ✅ Test structure mirrors src/
└── scripts/           # ✅ Utility scripts
```

## 🗂️ New Structure Details

### 📦 `/config` - Configuration Management
All configuration files centralized here:
- `settings.py` - Main application settings (from `enhanced_config.py`)
- `models.py` - Model configurations (LLM, embedding)
- `retrieval.py` - Retrieval-specific configs
- `logging_config.py` - Logging setup
- `legal_patterns.json` - Domain-specific patterns

### 🔧 `/src` - Source Code by RAG Phase

#### 1️⃣ `src/ingestion/` - Data Collection
```
ingestion/
├── crawlers/           # Web scrapers
│   └── thuvienphapluat_crawler.py
├── extractors/         # Content extraction
│   ├── vintern_batch_ocr.py
│   └── pdf-to-image.py
└── validators/         # Input validation
```

#### 2️⃣ `src/preprocessing/` - Text Cleaning & Parsing
```
preprocessing/
├── cleaners/           # Text normalization
├── parsers/            # Structure parsing
│   ├── md_processor.py
│   ├── optimal_chunker.py
│   └── utils.py
└── metadata/           # Metadata extraction
```

#### 3️⃣ `src/chunking/` - Document Chunking
```
chunking/
└── strategies/
    └── chunk-strategy.py
```

#### 4️⃣ `src/embedding/` - Vector Generation
```
embedding/
└── store/
    └── pgvector_store.py   # PostgreSQL vector storage
```

#### 5️⃣ `src/retrieval/` - **Query Enhancement & Retrieval** 🎯
**YOUR CURRENT FOCUS - Phase 3 (Query Enhancement)**

```
retrieval/
├── query_processing/          # Query enhancement
│   ├── query_enhancer.py      # Main enhancement module
│   ├── complexity_analyzer.py # Vietnamese query analysis
│   └── strategies/            # Enhancement strategies
│       ├── multi_query.py     # TODO: Multi-query generation
│       ├── hyde.py            # TODO: HyDE implementation
│       ├── step_back.py       # TODO: Step-back prompting
│       └── decomposition.py   # TODO: Query decomposition
│
├── retrievers/                # Retrieval implementations
│   ├── base_retriever.py      # Base retriever
│   └── adaptive_retriever.py  # Dynamic k retrieval
│
├── ranking/                   # Reranking logic
└── filters/                   # Post-retrieval filtering
```

#### 6️⃣ `src/generation/` - Response Generation
```
generation/
├── chains/                 # LangChain integrations
│   ├── qa_chain.py         # Basic QA chain
│   └── enhanced_chain.py   # Enhanced chain
├── prompts/                # Prompt templates
│   └── qa_prompts.py
├── formatters/             # Response formatting
└── validators/             # Response validation
```

#### 7️⃣ `src/evaluation/` - Metrics & Benchmarking
```
evaluation/
├── metrics/
│   └── retrieval_metrics.py
└── benchmarks/
```

### 🌐 `/api` - API Layer
```
api/
├── main.py             # FastAPI application
├── routers/            # API endpoints
├── schemas/            # Request/Response models
└── middleware/         # Auth, logging, etc.
```

### 🧪 `/tests` - Test Suite
```
tests/
├── unit/
│   └── test_retrieval/     # Mirrors src/retrieval/
├── integration/
└── fixtures/
```

## 🔄 Import Changes

### Old Imports → New Imports

**Configuration:**
```python
# Before
from app.core.enhanced_config import settings
from app.core.config import ModelConfig
from app.core.logging import setup_logging
from app.core.vectorstore import bootstrap

# After
from config.settings import settings
from config.models import ModelConfig
from config.logging_config import setup_logging
from src.embedding.store.pgvector_store import bootstrap
```

**Query Enhancement (Your current work):**
```python
# Before
from app.rag.query_enhancement import QueryEnhancer
from app.rag.QuestionComplexAnalyzer import QuestionComplexityAnalyzer

# After
from src.retrieval.query_processing.query_enhancer import QueryEnhancer
from src.retrieval.query_processing.complexity_analyzer import QuestionComplexityAnalyzer
```

**Retrieval:**
```python
# Before
from app.rag.retriever import BaseRetriever
from app.rag.adaptive_retriever import AdaptiveRetriever

# After
from src.retrieval.retrievers.base_retriever import BaseRetriever
from src.retrieval.retrievers.adaptive_retriever import AdaptiveRetriever
```

**Generation:**
```python
# Before
from app.rag.chain import answer
from app.rag.enhanced_chain import EnhancedChain
from app.rag.prompts import LEGAL_QA_PROMPT

# After
from src.generation.chains.qa_chain import answer
from src.generation.chains.enhanced_chain import EnhancedChain
from src.generation.prompts.qa_prompts import LEGAL_QA_PROMPT
```

**Evaluation:**
```python
# Before
from app.rag.eval import evaluate_retrieval

# After
from src.evaluation.metrics.retrieval_metrics import evaluate_retrieval
```

## 🚀 Migration Steps Completed

1. ✅ Created new directory structure
2. ✅ Moved files to appropriate locations
3. ✅ Created `__init__.py` files
4. ✅ Updated all imports automatically (34 changes in 17 files)
5. ✅ Verified structure with `tree` command

## 📝 Files Moved

### Config Files
- `app/core/enhanced_config.py` → `config/settings.py`
- `app/core/config.py` → `config/models.py`
- `app/core/logging.py` → `config/logging_config.py`
- `app/core/vectorstore.py` → `src/embedding/store/pgvector_store.py`

### Data Processing
- `app/data/crawler/thuvienphapluat_crawler.py` → `src/ingestion/crawlers/`
- `app/data/ocr-process/*` → `src/ingestion/extractors/`
- `app/data/core/md-preprocess/*` → `src/preprocessing/parsers/`
- `app/data/core/chunk-strategy.py` → `src/chunking/strategies/`

### RAG Components (Your focus area)
- `app/rag/query_enhancement.py` → `src/retrieval/query_processing/query_enhancer.py`
- `app/rag/QuestionComplexAnalyzer.py` → `src/retrieval/query_processing/complexity_analyzer.py`
- `app/rag/retriever.py` → `src/retrieval/retrievers/base_retriever.py`
- `app/rag/adaptive_retriever.py` → `src/retrieval/retrievers/adaptive_retriever.py`
- `app/rag/chain.py` → `src/generation/chains/qa_chain.py`
- `app/rag/enhanced_chain.py` → `src/generation/chains/enhanced_chain.py`
- `app/rag/prompts.py` → `src/generation/prompts/qa_prompts.py`
- `app/rag/eval.py` → `src/evaluation/metrics/retrieval_metrics.py`

### API
- `app/api/main.py` → `api/main.py` (copied)

## 🎯 Next Steps for Query Enhancement Module

Your current focus is on **Phase 5: Retrieval / Query Enhancement**. Here's what to implement next:

### 1. Complete Query Enhancement Strategies

Create individual strategy files in `src/retrieval/query_processing/strategies/`:

```bash
# Create strategy files
touch src/retrieval/query_processing/strategies/multi_query.py
touch src/retrieval/query_processing/strategies/hyde.py
touch src/retrieval/query_processing/strategies/step_back.py
touch src/retrieval/query_processing/strategies/decomposition.py
touch src/retrieval/query_processing/strategies/__init__.py
```

### 2. Implement Each Strategy

Follow the implementation guide provided earlier for:
- ✅ `multi_query.py` - Multi-query generation
- ✅ `hyde.py` - Hypothetical Document Embeddings
- ✅ `step_back.py` - Step-back prompting
- ✅ `decomposition.py` - Query decomposition

### 3. Update Main Enhancer

Refactor `src/retrieval/query_processing/query_enhancer.py` to use the new strategy pattern.

### 4. Add Tests

Create comprehensive tests in `tests/unit/test_retrieval/`:
```bash
touch tests/unit/test_retrieval/test_query_enhancer.py
touch tests/unit/test_retrieval/test_strategies.py
touch tests/unit/test_retrieval/test_complexity_analyzer.py
```

### 5. Integration

Update `src/retrieval/retrievers/adaptive_retriever.py` to use the enhanced query processor.

## 🛠️ Useful Commands

### View Structure
```bash
# Full src structure
tree -L 4 -I '__pycache__|*.pyc' src/

# Just retrieval module
tree -L 3 src/retrieval/

# Just your working files
tree -L 4 src/retrieval/query_processing/
```

### Find Files
```bash
# Find all retrieval-related files
find src/retrieval -name "*.py" -type f

# Find query enhancement files
find src/retrieval/query_processing -name "*.py"
```

### Run Tests
```bash
# All tests
pytest tests/

# Just retrieval tests
pytest tests/unit/test_retrieval/

# Specific test file
pytest tests/unit/test_retrieval/test_query_enhancer.py -v
```

### Check Imports
```bash
# Check for old imports still remaining
grep -r "from app\." src/ --include="*.py"
grep -r "import app\." src/ --include="*.py"
```

## 🔗 Related Documentation

- [Phase 1 Implementation Plan](../dev-log/phase 1.md)
- [Enhanced Pipeline](../dev-log/ENHANCED_PIPELINE.md)
- [Setup Guide](../setup.md)

## ⚠️ Important Notes

1. **Old `app/` directory still exists** - Contains original files as backup
   - Can be removed after thorough testing: `rm -rf app/`
   
2. **Imports have been auto-updated** - 34 changes in 17 files
   - Verify critical imports are working correctly
   
3. **Test before deleting old files**
   ```bash
   # Run tests to verify everything works
   pytest tests/ -v
   
   # Check for import errors
   python -c "from src.retrieval.query_processing.query_enhancer import QueryEnhancer"
   ```

4. **Phase 1 Demo still uses old path**
   - `app/rag/phase1_demo.py` has been updated but still in old location
   - Consider moving to `examples/` or `demos/` directory

## 📊 Migration Statistics

- **Total Python files**: 95
- **Files updated**: 17
- **Import changes**: 34
- **Directories created**: 31
- **Files moved**: ~20+

## ✅ Verification Checklist

- [x] Directory structure created
- [x] Files moved to new locations
- [x] `__init__.py` files created
- [x] Imports updated automatically
- [ ] Run all tests successfully
- [ ] Verify critical paths work
- [ ] Update documentation
- [ ] Remove old `app/` directory
- [ ] Update CI/CD pipelines (if any)
- [ ] Update Docker files (if needed)

---

**🎉 Restructure completed successfully!**

For questions or issues, check the migration scripts:
- `scripts/migrate_structure.sh` - File migration
- `scripts/update_imports.py` - Import updates
