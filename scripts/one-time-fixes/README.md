# One-Time Fixes

Scripts trong folder này là các migration/fix một lần duy nhất, đã được chạy rồi và **không nên chạy lại** trừ khi có vấn đề.

## Scripts

### Migration Scripts

- `migrate_document_ids.py` - Migrate document IDs sang format mới (Option 4: Hybrid System)
- `migrate_reprocessed_to_processed.py` - Rename directories từ 'reprocessed' → 'processed'
- `fix_migration_links.py` - Backfill documents table và fix inconsistencies
- `migrate_structure.sh` - Restructure data folders
- `verify_migration.sh` - Verify migration results

### Code Update Scripts

- `update_imports.py` - Update imports sau khi restructure project
- `build_document_name_mapping.py` - Build document_id → document_name mapping

## ⚠️ Warning

**KHÔNG chạy các scripts này nếu không chắc chắn!** Chúng có thể:

- Modify database schema
- Rename directories
- Update code references
- Change document IDs

Nếu cần chạy lại, hãy:

1. Backup database trước: `scripts/utilities/db/create_dump.sh`
2. Review code để hiểu script làm gì
3. Test trên môi trường development trước
