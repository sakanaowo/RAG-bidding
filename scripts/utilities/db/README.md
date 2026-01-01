# Database Utilities

Scripts để import/export data và optimize database.

## Data Export

### `export_database.py`

Export embeddings và metadata ở nhiều formats (JSON, CSV, NPY).

```bash
python scripts/utilities/db/export_database.py
```

**Output:** Exported files in `data/exports/`

### `export_all_data.sh`

Export tất cả data từ database.

```bash
bash scripts/utilities/db/export_all_data.sh
```

## Data Import

### `import_chunks.py`

Import chunks từ JSONL files vào database.

```bash
python scripts/utilities/db/import_chunks.py
```

### `import_processed_chunks.py`

Import processed chunks với metadata.

```bash
python scripts/utilities/db/import_processed_chunks.py
```

## Backup & Restore

### `create_dump.sh`

Tạo PostgreSQL dump.

```bash
bash scripts/utilities/db/create_dump.sh
```

**Output:** `backup_YYYYMMDD_HHMMSS.sql`

### `restore_dump.sh`

Restore database từ dump file.

```bash
bash scripts/utilities/db/restore_dump.sh <dump_file.sql>
```

**⚠️ Warning:** Sẽ DROP existing database!

## Optimization

### `optimize_postgresql.sh`

Apply PostgreSQL optimizations (connection pooling, memory, query planner).

```bash
bash scripts/utilities/db/optimize_postgresql.sh
```

**Changes:**

- `shared_buffers`
- `effective_cache_size`
- `work_mem`
- `maintenance_work_mem`
- Connection pool settings

**Note:** Cần restart PostgreSQL sau khi chạy

## Best Practices

### Before Production Deployment

1. Run `create_dump.sh` - Backup current state
2. Run `optimize_postgresql.sh` - Apply optimizations
3. Restart PostgreSQL
4. Test performance

### Data Migration

1. Export với `export_database.py` hoặc `create_dump.sh`
2. Migrate/transform data nếu cần
3. Import với `import_chunks.py` hoặc `restore_dump.sh`
4. Verify data integrity

### Regular Maintenance

- Weekly backup: `create_dump.sh`
- Monitor database size
- VACUUM ANALYZE định kỳ (tự động trong PostgreSQL)
- Review `optimize_postgresql.sh` settings theo workload
