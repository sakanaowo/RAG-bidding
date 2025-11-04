# 🧪 Tests Directory

Unit and integration tests for the RAG system.

## 📁 Directory Structure

### `/unit/`
Unit tests for individual components and modules.

### `/integration/`
**Integration tests:**
- Enhanced source tests
- Enhancer quick tests
- Multiple sources tests

### `/retrieval/`
**Retrieval and filtering tests:**
- API with filtering tests
- Status filtering tests

### `/reranking/`
**Reranking model tests:**
- BGE reranker tests
- PhoBERT reranker tests
- PhoBERT setup tests
- End-to-end reranking tests
- Model comparison tests

## 🚀 Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Category
```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Retrieval tests
python -m pytest tests/retrieval/ -v

# Reranking tests
python -m pytest tests/reranking/ -v
```

## 📊 Test Categories

| Category | Purpose |
|----------|---------|
| Unit | Component-level testing |
| Integration | Multi-component workflows |
| Retrieval | Search and filtering |
| Reranking | Result reordering models |

## 🔗 Related

- [Script Tests](../scripts/test/) - Pipeline and preprocessing tests
- [Source Code](../src/) - Implementation
