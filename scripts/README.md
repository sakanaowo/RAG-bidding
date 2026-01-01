# Scripts Directory

Organized collection của operational scripts cho RAG Bidding System.

## 📁 Directory Structure

```
scripts/
├── README.md                          # This file
├── __init__.py
│
├── 🚀 CORE SCRIPTS (root level)
├── bootstrap_db.py                    # Initialize database
├── process_and_import_new_docs.py     # Main ingestion pipeline
├── setup_alembic.py                   # Database migrations setup
├── test_db_connection.py              # Database connection test
├── test_sqlalchemy.sh                 # SQLAlchemy test
│
├── 📂 one-time-fixes/                 # Migration & fix scripts (run once)
│   ├── README.md
│   ├── fix_migration_links.py
│   ├── migrate_document_ids.py
│   ├── migrate_reprocessed_to_processed.py
│   ├── migrate_structure.sh
│   ├── verify_migration.sh
│   ├── update_imports.py
│   └── build_document_name_mapping.py
│
├── 📂 maintenance/                    # Periodic maintenance scripts
│   ├── README.md
│   ├── batch_reprocess_all.py         # Batch reprocessing
│   ├── reprocess_and_reembed.py       # Reprocess + re-embed
│   └── enrich_and_reembed.py          # Enrich + re-embed
│
├── 📂 analysis/                       # Analysis & debugging tools
│   ├── README.md
│   ├── benchmark_retrieval.py         # Performance benchmarking
│   ├── calculate_embedding_cost.py    # Cost analysis
│   ├── explain_optimizations.py       # DB optimization analysis
│   ├── summarize_batch.py             # Batch results summary
│   ├── debug_metadata.py              # Debug metadata extraction
│   └── test_pipeline_dry_run.py       # Pipeline testing
│
├── 📂 utilities/                      # Utility scripts
│   └── db/                            # Database utilities
│       ├── README.md
│       ├── export_database.py         # Export data
│       ├── import_chunks.py           # Import chunks
│       ├── import_processed_chunks.py # Import processed chunks
│       ├── create_dump.sh             # Create DB dump
│       ├── export_all_data.sh         # Export all data
│       ├── restore_dump.sh            # Restore DB dump
│       └── optimize_postgresql.sh     # PostgreSQL optimization
│
├── 📂 tests/                          # Test suite (merged from test/)
│   ├── README.md
│   ├── TEST_README.md
│   ├── run_all_tests.py               # Test runner
│   ├── test_*.py                      # Various test scripts
│   ├── chunking/
│   ├── integration/
│   ├── performance/
│   ├── pipeline/
│   ├── preprocessing/
│   ├── reranking/
│   ├── retrieval/
│   └── unit/
│
├── 📂 migration/                      # Alembic migration files
│   ├── README.md
│   └── *.sql, *.py                    # Migration scripts
│
├── 📂 debug/                          # Debug scripts
│   ├── debug_chunks_issue.py
│   └── debug_full_pipeline.py
│
└── 📂 examples/                       # Usage examples
    └── sqlalchemy_usage.py            # SQLAlchemy usage examples
```

## 🎯 Quick Start Guide

### For New Developers

1. **Setup Database:**

   ```bash
   python scripts/bootstrap_db.py
   python scripts/setup_alembic.py
   ```

2. **Test Connection:**

   ```bash
   python scripts/test_db_connection.py
   bash scripts/test_sqlalchemy.sh
   ```

3. **Run Tests:**
   ```bash
   python scripts/tests/run_all_tests.py
   ```

### For Operations

1. **Add New Documents:**

   ```bash
   python scripts/process_and_import_new_docs.py
   ```

2. **Backup Database:**

   ```bash
   bash scripts/utilities/db/create_dump.sh
   ```

3. **Performance Analysis:**
   ```bash
   python scripts/analysis/benchmark_retrieval.py
   python scripts/analysis/explain_optimizations.py
   ```

### For Maintenance

1. **Reprocess Documents:**

   ```bash
   python scripts/maintenance/batch_reprocess_all.py
   ```

2. **Re-embed with New Model:**

   ```bash
   python scripts/maintenance/reprocess_and_reembed.py
   ```

3. **Optimize Database:**
   ```bash
   bash scripts/utilities/db/optimize_postgresql.sh
   ```

## 📋 Script Categories

### 🚀 Core Scripts (Root Level)

Scripts được sử dụng thường xuyên, liên quan trực tiếp tới hệ thống chính.

**When to use:**

- Daily operations
- Development workflow
- System initialization

### 📂 one-time-fixes/

Scripts migration và fix lỗi một lần duy nhất.

**⚠️ DO NOT run unless you know what you're doing!**

**When to use:**

- Never (đã chạy rồi)
- Only for reference hoặc adapting for new migrations

### 📂 maintenance/

Scripts bảo trì định kỳ cho hệ thống.

**When to use:**

- Weekly/monthly maintenance
- After major updates
- When reprocessing needed

### 📂 analysis/

Tools để analyze performance và debug issues.

**When to use:**

- Performance tuning
- Troubleshooting
- Cost optimization
- Before/after batch processing

### 📂 utilities/

General-purpose utilities, especially database operations.

**When to use:**

- Data import/export
- Backup/restore
- Database optimization
- Regular maintenance

### 📂 tests/

Comprehensive test suite.

**When to use:**

- Before deployment
- After code changes
- CI/CD pipeline
- Feature validation

## 🔧 Development Guidelines

### Adding New Scripts

1. **Determine category:**

   - Core operation → root level
   - One-time fix → `one-time-fixes/`
   - Periodic task → `maintenance/`
   - Analysis/debug → `analysis/`
   - Utility → `utilities/`
   - Test → `tests/`

2. **Follow naming convention:**

   - Descriptive names: `verb_noun.py` (e.g., `export_database.py`)
   - Test prefix: `test_*.py`
   - Migration: numbered `001_description.py`

3. **Add documentation:**

   - Docstring at top of file
   - Usage examples
   - Update folder README.md

4. **Include error handling:**
   - Graceful failures
   - Helpful error messages
   - Rollback for destructive operations

### Best Practices

1. **Always backup before destructive operations**

   ```bash
   bash scripts/utilities/db/create_dump.sh
   ```

2. **Test in dry-run mode first**

   ```bash
   python script.py --dry-run
   ```

3. **Use logging instead of print**

   ```python
   import logging
   logging.info("Operation started")
   ```

4. **Add progress indicators for long operations**

   ```python
   from tqdm import tqdm
   for item in tqdm(items):
       process(item)
   ```

5. **Document expected runtime**
   ```python
   # Expected runtime: ~30 minutes for 1000 documents
   ```

## 🚨 Emergency Procedures

### Database Issues

1. **Connection failures:**

   ```bash
   python scripts/test_db_connection.py
   ```

2. **Restore from backup:**

   ```bash
   bash scripts/utilities/db/restore_dump.sh backup_file.sql
   ```

3. **Re-initialize:**
   ```bash
   python scripts/bootstrap_db.py
   ```

### Data Corruption

1. **Export current state:**

   ```bash
   python scripts/utilities/db/export_database.py
   ```

2. **Reprocess from raw:**
   ```bash
   python scripts/maintenance/batch_reprocess_all.py
   ```

### Performance Degradation

1. **Run benchmarks:**

   ```bash
   python scripts/analysis/benchmark_retrieval.py
   ```

2. **Check query plans:**

   ```bash
   python scripts/analysis/explain_optimizations.py
   ```

3. **Apply optimizations:**
   ```bash
   bash scripts/utilities/db/optimize_postgresql.sh
   ```

## 📚 Related Documentation

- Database Schema: `/documents/System Design/03_Database_Schema.md`
- SQLAlchemy Guide: `/documents/System Design/06_SQLAlchemy_Implementation.md`
- Quick Start ORM: `/documents/System Design/08_Quick_Start_ORM.md`
- API Specification: `/documents/System Design/05_API_Specification.md`

## 🔗 Links

- **Project Root:** `/home/sakana/Code/RAG-bidding`
- **Source Code:** `/src`
- **Documentation:** `/documents/System Design`
- **Data:** `/data`
- **Logs:** `/logs`

---

**Last Updated:** 2025-11-25  
**Maintainer:** Development Team
