# Maintenance Scripts

Scripts bảo trì định kỳ cho hệ thống - reprocessing, re-embedding, enrichment.

## Scripts

### Batch Processing

- `batch_reprocess_all.py` - Batch re-processing tất cả raw documents với unified pipeline
  ```bash
  python scripts/maintenance/batch_reprocess_all.py
  ```

### Re-embedding

- `reprocess_and_reembed.py` - Reprocess và re-embed documents

  ```bash
  python scripts/maintenance/reprocess_and_reembed.py
  ```

- `enrich_and_reembed.py` - Enrich existing chunks với semantic metadata rồi re-embed
  ```bash
  python scripts/maintenance/enrich_and_reembed.py
  ```

## Use Cases

### Khi nào cần reprocess?

- Có chunks lỗi hoặc incomplete
- Thay đổi chunking strategy
- Update preprocessing pipeline

### Khi nào cần re-embed?

- Đổi embedding model (e.g., text-embedding-3-large)
- Embedding dimension thay đổi
- Thêm metadata mới vào chunks

### Khi nào cần enrich?

- Thêm semantic metadata (summary, keywords, categories)
- Cải thiện retrieval quality
- Prepare cho advanced features (faceted search, classification)

## ⚠️ Notes

- Scripts này có thể chạy lâu (hours) với dataset lớn
- Nên chạy trong `screen` hoặc `tmux` session
- Monitor memory usage (embeddings có thể consume nhiều RAM)
- Backup database trước khi reprocess large batches
