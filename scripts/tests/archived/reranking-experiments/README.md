# Archived Reranking Experiments

**Archived**: 2025-12-24  
**Reason**: PhoBERT experiments - not used in production

## Files

1. `test_phobert_reranker.py` - Test PhoBERT class implementation
2. `test_phobert_setup.py` - Setup verification for PhoBERT
3. `test_model_comparison.py` - BGE vs PhoBERT comparison
4. `test_end_to_end_reranking.py` - E2E reranking test

## Context

These tests were part of Phase 2 reranker evaluation (Nov 2025).

**Conclusion**: BGE reranker (BAAI/bge-reranker-v2-m3) was selected for production.

**Production Reranker**: `src/retrieval/ranking/bge_reranker.py`

## Reference

- See: `documents/technical/reranking-analysis/SINGLETON_PATTERN_GUIDE.md`
- See: `documents/technical/reranking-analysis/RERANKING_STRATEGIES.md`
