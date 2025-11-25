# Analysis & Debugging Scripts

Scripts để analyze performance, debug issues, và tính toán metrics.

## Performance Analysis

### `benchmark_retrieval.py`

Performance benchmarking cho RAG system - tests retrieval với diverse queries.

```bash
python scripts/analysis/benchmark_retrieval.py
```

**Output:** Performance metrics across different k values và filters

### `calculate_embedding_cost.py`

Tính toán embedding costs dựa trên token count.

```bash
python scripts/analysis/calculate_embedding_cost.py
```

**Output:** Token count, API cost estimates

### `explain_optimizations.py`

Analyze database query plans và optimization opportunities.

```bash
python scripts/analysis/explain_optimizations.py
```

**Output:** EXPLAIN ANALYZE results, index suggestions

## Debugging Tools

### `debug_metadata.py`

Debug metadata extraction từ DOCX files.

```bash
python scripts/analysis/debug_metadata.py <path/to/file.docx>
```

**Use case:** Khi metadata không được extract đúng

### `test_pipeline_dry_run.py`

Test pipeline với files thực tế trong `data/raw`.

```bash
python scripts/analysis/test_pipeline_dry_run.py
```

**Use case:** Verify pipeline trước khi batch processing

## Summary Tools

### `summarize_batch.py`

Quick summary của batch reprocessing results.

```bash
python scripts/analysis/summarize_batch.py
```

**Output:**

- Number of chunk files
- Number of metadata files
- Document types distribution
- Categories distribution

## Usage Tips

1. **Before large batch processing:** Run `test_pipeline_dry_run.py`
2. **After batch processing:** Run `summarize_batch.py`
3. **Performance issues:** Run `benchmark_retrieval.py` + `explain_optimizations.py`
4. **Cost optimization:** Run `calculate_embedding_cost.py`
5. **Metadata issues:** Run `debug_metadata.py` on problematic files
