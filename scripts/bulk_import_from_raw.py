#!/usr/bin/env python3
"""
Bulk Import Script - Import tài liệu từ data/raw
=================================================

Script này sẽ:
1. Import files từ data/raw theo từng folder
2. Không cần authentication (direct database access)
3. Sử dụng WorkingUploadPipeline
4. Store embeddings vào vector database

Usage:
    python scripts/bulk_import_from_raw.py [--dry-run] [--folder FOLDER]

Examples:
    # Interactive mode - chọn folder để import
    python scripts/bulk_import_from_raw.py

    # Dry run - chỉ liệt kê files
    python scripts/bulk_import_from_raw.py --dry-run

    # Import 1 folder cụ thể
    python scripts/bulk_import_from_raw.py --folder "Luat chinh"

    # Import tất cả folders
    python scripts/bulk_import_from_raw.py --all
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.database import get_db_sync
from src.config.embedding_provider import get_default_embeddings
from src.preprocessing.upload_pipeline import WorkingUploadPipeline
from src.embedding.store.pgvector_store import PGVectorStore
from langchain_core.documents import Document

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}


# Category mapping từ folder name sang database category
CATEGORY_MAPPING = {
    "Luat chinh": "Luật chính",
    "Nghi dinh": "Nghị định",
    "Thong tu": "Thông tư",
    "Quyet dinh": "Quyết định",
    "Ho so moi thau": "Hồ sơ mời thầu",
    "Mau bao cao": "Mẫu báo cáo",
    "Cau hoi thi": "Câu hỏi thi",
}

# Document type mapping
DOC_TYPE_MAPPING = {
    "Luật chính": "law",
    "Nghị định": "decree",
    "Thông tư": "circular",
    "Quyết định": "decision",
    "Hồ sơ mời thầu": "bidding",
    "Mẫu báo cáo": "template",
    "Câu hỏi thi": "exam",
}


class BulkImporter:
    """Bulk importer cho data/raw với CASCADE checking"""

    def __init__(self, raw_data_path: Path):
        self.raw_data_path = raw_data_path
        self.pipeline = WorkingUploadPipeline(enable_enrichment=True)
        self.vector_store = PGVectorStore()

        # Statistics
        self.stats = {
            "total_files": 0,
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "total_chunks": 0,
            "errors": [],
        }

    def check_cascade_constraints(self) -> Dict[str, bool]:
        """
        Kiểm tra các FK constraints có ON DELETE CASCADE không

        Returns:
            Dict với constraint names và status
        """
        logger.info("🔍 Checking CASCADE DELETE constraints...")

        conn = get_db_sync()
        cursor = conn.cursor()

        # Query để lấy tất cả FK constraints liên quan đến documents và document_chunks
        cursor.execute(
            """
            SELECT 
                tc.table_name,
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND (ccu.table_name IN ('documents', 'document_chunks'))
            ORDER BY tc.table_name, tc.constraint_name;
        """
        )

        constraints = cursor.fetchall()
        conn.close()

        results = {}
        issues = []

        logger.info("\n📋 Foreign Key Constraints:\n")
        logger.info(
            f"{'Table':<25} {'Column':<25} {'→ References':<30} {'Delete Rule':<15}"
        )
        logger.info("=" * 95)

        for row in constraints:
            table, constraint, column, ref_table, ref_column, delete_rule = row
            reference = f"{ref_table}.{ref_column}"

            # Check if CASCADE
            is_cascade = delete_rule == "CASCADE"
            status = "✅ CASCADE" if is_cascade else "⚠️  SET NULL/NO ACTION"

            logger.info(f"{table:<25} {column:<25} → {reference:<30} {status:<15}")

            results[constraint] = is_cascade

            # Track issues
            if not is_cascade and ref_table in ["documents", "document_chunks"]:
                issues.append(
                    {
                        "table": table,
                        "column": column,
                        "reference": reference,
                        "delete_rule": delete_rule,
                        "constraint": constraint,
                    }
                )

        logger.info("=" * 95)

        if issues:
            logger.warning("\n⚠️  WARNINGS - Constraints không có CASCADE:")
            for issue in issues:
                logger.warning(
                    f"  - {issue['table']}.{issue['column']} → {issue['reference']} "
                    f"(Rule: {issue['delete_rule']}, Constraint: {issue['constraint']})"
                )
            logger.warning("\n💡 Để fix, chạy:")
            for issue in issues:
                logger.warning(
                    f"  ALTER TABLE {issue['table']} DROP CONSTRAINT {issue['constraint']};"
                )
                logger.warning(
                    f"  ALTER TABLE {issue['table']} ADD CONSTRAINT {issue['constraint']} "
                    f"FOREIGN KEY ({issue['column']}) REFERENCES {issue['reference'].split('.')[0]}({issue['reference'].split('.')[1]}) "
                    f"ON DELETE CASCADE;"
                )
        else:
            logger.info("\n✅ All constraints have proper CASCADE DELETE rules!")

        return results

    def discover_files(
        self, category_filter: str = None
    ) -> List[Tuple[Path, str, str]]:
        """
        Discover tất cả files trong data/raw

        Args:
            category_filter: Nếu set, chỉ process folder này (có thể là folder name hoặc category name)

        Returns:
            List of (file_path, category, doc_type)
        """
        files = []
        supported_exts = self.pipeline.get_supported_extensions()

        logger.info(f"\n🔍 Scanning {self.raw_data_path}...")

        # Scan each category folder
        for category_folder in self.raw_data_path.iterdir():
            if not category_folder.is_dir():
                continue

            folder_name = category_folder.name
            category = CATEGORY_MAPPING.get(folder_name, folder_name)
            doc_type = DOC_TYPE_MAPPING.get(category, "other")

            # Filter by category if specified (match either folder name or category name)
            if category_filter:
                if folder_name != category_filter and category != category_filter:
                    continue

            # Find all supported files
            category_files = []
            for ext in supported_exts:
                category_files.extend(category_folder.glob(f"**/*{ext}"))

            for file_path in category_files:
                files.append((file_path, category, doc_type))

            logger.info(
                f"  📁 {folder_name:<30} → {len(category_files):>3} files ({category})"
            )

        return files

    def import_file(
        self, file_path: Path, category: str, doc_type: str
    ) -> Tuple[bool, str, int]:
        """
        Import một file vào database

        Returns:
            (success, document_id, num_chunks)
        """
        try:
            logger.info(f"\n📄 Processing: {file_path.name}")

            # Step 1: Process through pipeline
            success, chunks, error_msg = self.pipeline.process_file(
                file_path=file_path,
                document_type=doc_type,
                batch_name=f"bulk_import_{datetime.now().strftime('%Y%m%d')}",
            )

            if not success:
                logger.error(f"  ❌ Pipeline failed: {error_msg}")
                return False, None, 0

            if not chunks:
                logger.warning(f"  ⚠️  No chunks generated")
                return False, None, 0

            logger.info(f"  ✅ Generated {len(chunks)} chunks")

            # Step 2: Convert to LangChain Documents
            documents = []
            for chunk in chunks:
                chunk_metadata = chunk.to_dict()
                chunk_metadata.pop("content", None)
                doc = Document(page_content=chunk.content, metadata=chunk_metadata)
                documents.append(doc)

            # Step 3: Store embeddings
            logger.info(f"  🔄 Storing embeddings...")
            self.vector_store.add_documents(documents)
            logger.info(f"  ✅ Stored {len(documents)} embeddings")

            # Step 4: Insert into documents table
            first_chunk = chunks[0]
            document_id = first_chunk.document_id
            document_name = (
                first_chunk.extra_metadata.get("document_title")
                or first_chunk.extra_metadata.get("title")
                or first_chunk.section_title
                or file_path.stem
            )

            doc_uuid = self._insert_document_record(
                document_id=document_id,
                document_name=document_name,
                document_type=doc_type,
                category=category,
                filename=file_path.name,
                source_file=str(file_path),
                total_chunks=len(chunks),
            )

            # Step 5: Insert chunks into document_chunks table
            logger.info(f"  🔄 Inserting chunks into document_chunks...")
            chunk_id_map = self._insert_chunks(doc_uuid, chunks)

            # Step 6: Update langchain_pg_embedding with chunk_id references
            logger.info(f"  🔄 Linking embeddings to chunks...")
            self._update_embedding_chunk_ids(chunk_id_map)

            logger.info(f"  ✅ Document saved: {document_id}")
            return True, document_id, len(chunks)

        except Exception as e:
            logger.error(f"  ❌ Error: {str(e)}", exc_info=True)
            return False, None, 0

    def _insert_document_record(
        self,
        document_id: str,
        document_name: str,
        document_type: str,
        category: str,
        filename: str,
        source_file: str,
        total_chunks: int,
    ):
        """Insert document record vào documents table"""
        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            # Truncate document_name if too long
            if len(document_name) > 500:
                logger.warning(
                    f"⚠️  Document name too long ({len(document_name)} chars), truncating"
                )
                document_name = document_name[:497] + "..."

            cursor.execute(
                """
                INSERT INTO documents (
                    document_id, document_name, document_type, category,
                    filename, source_file, total_chunks, status,
                    created_at, updated_at
                ) VALUES (
                    %(document_id)s, %(document_name)s, %(document_type)s, %(category)s,
                    %(filename)s, %(source_file)s, %(total_chunks)s, 'active',
                    NOW(), NOW()
                )
                ON CONFLICT (document_id) DO UPDATE SET
                    document_name = EXCLUDED.document_name,
                    total_chunks = EXCLUDED.total_chunks,
                    updated_at = NOW()
                RETURNING id
            """,
                {
                    "document_id": document_id,
                    "document_name": document_name,
                    "document_type": document_type,
                    "category": category,
                    "filename": filename,
                    "source_file": source_file,
                    "total_chunks": total_chunks,
                },
            )

            result = cursor.fetchone()
            doc_uuid = result[0] if result else None
            conn.commit()
            return doc_uuid

        except Exception as e:
            logger.error(f"Failed to insert document: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _insert_chunks(self, doc_uuid, chunks: list) -> dict:
        """
        Insert chunks vào document_chunks table và trả về mapping chunk_id -> uuid

        Returns:
            Dict mapping chunk_id string -> chunk UUID
        """
        conn = None
        chunk_id_map = {}

        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            for chunk in chunks:
                chunk_dict = chunk.to_dict()
                chunk_id = (
                    chunk_dict.get("chunk_id")
                    or f"{chunk_dict.get('document_id')}_{chunk_dict.get('chunk_index', 0)}"
                )

                cursor.execute(
                    """
                    INSERT INTO document_chunks (
                        document_id, chunk_id, content, chunk_index,
                        section_title, hierarchy_path, keywords,
                        char_count, created_at, updated_at
                    ) VALUES (
                        %(document_id)s, %(chunk_id)s, %(content)s, %(chunk_index)s,
                        %(section_title)s, %(hierarchy_path)s, %(keywords)s,
                        %(char_count)s, NOW(), NOW()
                    )
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = NOW()
                    RETURNING id
                """,
                    {
                        "document_id": doc_uuid,
                        "chunk_id": chunk_id,
                        "content": chunk.content,
                        "chunk_index": chunk_dict.get("chunk_index", 0),
                        "section_title": chunk_dict.get("section_title"),
                        "hierarchy_path": chunk_dict.get("hierarchy_path"),
                        "keywords": chunk_dict.get("keywords"),
                        "char_count": len(chunk.content),
                    },
                )

                result = cursor.fetchone()
                if result:
                    chunk_id_map[chunk_id] = result[0]

            conn.commit()
            logger.info(
                f"  ✅ Inserted {len(chunk_id_map)} chunks into document_chunks"
            )
            return chunk_id_map

        except Exception as e:
            logger.error(f"Failed to insert chunks: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _update_embedding_chunk_ids(self, chunk_id_map: dict):
        """
        Update langchain_pg_embedding để set chunk_id reference
        """
        if not chunk_id_map:
            return

        conn = None
        try:
            conn = get_db_sync()
            cursor = conn.cursor()

            updated = 0
            for chunk_id_str, chunk_uuid in chunk_id_map.items():
                # Update embeddings where cmetadata contains this chunk_id
                cursor.execute(
                    """
                    UPDATE langchain_pg_embedding 
                    SET chunk_id = %(chunk_uuid)s
                    WHERE cmetadata->>'chunk_id' = %(chunk_id)s
                    AND chunk_id IS NULL
                """,
                    {"chunk_uuid": chunk_uuid, "chunk_id": chunk_id_str},
                )
                updated += cursor.rowcount

            conn.commit()
            if updated > 0:
                logger.info(f"  ✅ Updated {updated} embedding chunk_id references")

        except Exception as e:
            logger.error(f"Failed to update embedding chunk_ids: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def run(self, dry_run: bool = False, category_filter: str = None):
        """
        Main import logic

        Args:
            dry_run: If True, chỉ list files không import
            category_filter: Nếu set, chỉ import category này
        """
        start_time = time.time()

        logger.info("=" * 100)
        logger.info("🚀 BULK IMPORT FROM data/raw")
        logger.info("=" * 100)

        # Step 1: Check CASCADE constraints
        constraints = self.check_cascade_constraints()

        # Step 2: Discover files
        files = self.discover_files(category_filter)
        self.stats["total_files"] = len(files)

        if not files:
            logger.warning("\n⚠️  No files found to import!")
            return

        logger.info(f"\n📊 Found {len(files)} files to process")

        if dry_run:
            logger.info("\n🔍 DRY RUN - Listing files only:\n")
            for file_path, category, doc_type in files:
                logger.info(
                    f"  - {file_path.relative_to(self.raw_data_path)} ({category})"
                )
            return

        # Step 3: Process files
        logger.info("\n" + "=" * 100)
        logger.info("📦 Starting import...")
        logger.info("=" * 100)

        for i, (file_path, category, doc_type) in enumerate(files, 1):
            logger.info(f"\n[{i}/{len(files)}] {category} - {file_path.name}")

            success, document_id, num_chunks = self.import_file(
                file_path, category, doc_type
            )

            if success:
                self.stats["processed"] += 1
                self.stats["total_chunks"] += num_chunks
            else:
                self.stats["failed"] += 1
                self.stats["errors"].append(
                    {"file": str(file_path), "category": category}
                )

        # Step 4: Summary
        elapsed = time.time() - start_time
        self._print_summary(elapsed)
        return self.stats["failed"] == 0

    def run_folder(self, folder_name: str, dry_run: bool = False) -> bool:
        """
        Import một folder cụ thể

        Args:
            folder_name: Tên folder (e.g., "Luat chinh")
            dry_run: Chỉ liệt kê files

        Returns:
            True nếu thành công
        """
        folder_path = self.raw_data_path / folder_name
        if not folder_path.exists():
            logger.error(f"❌ Folder không tồn tại: {folder_path}")
            return False

        logger.info(f"\n📂 Importing folder: {folder_name}")
        logger.info("=" * 60)

        return self.run(dry_run=dry_run, category_filter=folder_name)

    def get_available_folders(self) -> list[tuple[str, int]]:
        """
        Liệt kê các folders có sẵn trong data/raw

        Returns:
            List of (folder_name, file_count)
        """
        folders = []
        for item in sorted(self.raw_data_path.iterdir()):
            if item.is_dir():
                # Count files
                file_count = sum(
                    1
                    for f in item.rglob("*")
                    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
                )
                folders.append((item.name, file_count))
        return folders

    def _print_summary(self, elapsed_time: float):
        """Print import summary"""
        logger.info("\n" + "=" * 100)
        logger.info("📊 IMPORT SUMMARY")
        logger.info("=" * 100)

        logger.info(f"\n⏱️  Time elapsed: {elapsed_time:.2f}s")
        logger.info(f"\n📈 Statistics:")
        logger.info(f"  Total files:     {self.stats['total_files']}")
        logger.info(f"  ✅ Processed:     {self.stats['processed']}")
        logger.info(f"  ❌ Failed:        {self.stats['failed']}")
        logger.info(f"  ⏭️  Skipped:       {self.stats['skipped']}")
        logger.info(f"  📦 Total chunks:  {self.stats['total_chunks']}")

        if self.stats["processed"] > 0:
            logger.info(
                f"  📊 Avg chunks/doc: {self.stats['total_chunks'] / self.stats['processed']:.1f}"
            )
            logger.info(
                f"  ⚡ Avg time/doc:   {elapsed_time / self.stats['processed']:.2f}s"
            )

        if self.stats["errors"]:
            logger.error(f"\n❌ Failed files ({len(self.stats['errors'])}):")
            for error in self.stats["errors"]:
                logger.error(f"  - {error['file']} ({error['category']})")

        logger.info("\n" + "=" * 100)

        if self.stats["failed"] == 0:
            logger.info("✅ ALL IMPORTS SUCCESSFUL!")
        else:
            logger.warning(
                f"⚠️  {self.stats['failed']}/{self.stats['total_files']} files failed"
            )

        logger.info("=" * 100)


def interactive_mode(importer: BulkImporter, dry_run: bool = False):
    """
    Chế độ interactive - chọn folder để import
    """
    print("\n" + "=" * 60)
    print("🗂️  BULK IMPORT - INTERACTIVE MODE")
    print("=" * 60)

    # Get available folders
    folders = importer.get_available_folders()

    if not folders:
        print("❌ Không có folder nào trong data/raw")
        return

    while True:
        print(f"\n📂 Các folder có sẵn trong data/raw:")
        print("-" * 40)
        for i, (name, count) in enumerate(folders, 1):
            print(f"  {i}. {name} ({count} files)")
        print(f"  {len(folders) + 1}. Import tất cả folders")
        print(f"  0. Thoát")
        print("-" * 40)

        try:
            choice = input("\n👉 Chọn số folder (0 để thoát): ").strip()

            if choice == "0":
                print("👋 Bye!")
                break

            choice_num = int(choice)

            if choice_num == len(folders) + 1:
                # Import all
                confirm = (
                    input(
                        f"\n⚠️  Import TẤT CẢ {sum(c for _, c in folders)} files? (y/n): "
                    )
                    .strip()
                    .lower()
                )
                if confirm == "y":
                    for folder_name, _ in folders:
                        print(f"\n{'='*60}")
                        success = importer.run_folder(folder_name, dry_run=dry_run)
                        if not success:
                            print(f"⚠️  Folder {folder_name} có lỗi, tiếp tục...")
                        # Reset stats for next folder
                        importer.stats = {
                            "total_files": 0,
                            "processed": 0,
                            "failed": 0,
                            "skipped": 0,
                            "total_chunks": 0,
                            "errors": [],
                        }
                    print("\n✅ Hoàn thành import tất cả folders!")
                break

            elif 1 <= choice_num <= len(folders):
                folder_name, file_count = folders[choice_num - 1]
                confirm = (
                    input(f"\n📁 Import {folder_name} ({file_count} files)? (y/n): ")
                    .strip()
                    .lower()
                )
                if confirm == "y":
                    importer.run_folder(folder_name, dry_run=dry_run)

                # Ask if continue
                cont = input("\n🔄 Import folder khác? (y/n): ").strip().lower()
                if cont != "y":
                    print("👋 Bye!")
                    break
                # Reset stats for next folder
                importer.stats = {
                    "total_files": 0,
                    "processed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total_chunks": 0,
                    "errors": [],
                }
            else:
                print("❌ Số không hợp lệ!")

        except ValueError:
            print("❌ Vui lòng nhập số!")
        except KeyboardInterrupt:
            print("\n👋 Bye!")
            break


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Bulk import documents from data/raw folder by folder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode - chọn folder để import
  python scripts/bulk_import_from_raw.py
  
  # Dry run - chỉ liệt kê files
  python scripts/bulk_import_from_raw.py --dry-run
  
  # Import 1 folder cụ thể
  python scripts/bulk_import_from_raw.py --folder "Luat chinh"
  
  # Import tất cả folders lần lượt
  python scripts/bulk_import_from_raw.py --all
  
  # Liệt kê folders
  python scripts/bulk_import_from_raw.py --list
        """,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="List files only, don't import"
    )

    parser.add_argument(
        "--folder",
        type=str,
        help="Import specific folder (e.g., 'Luat chinh', 'Nghi dinh')",
    )

    parser.add_argument(
        "--all", action="store_true", help="Import all folders sequentially"
    )

    parser.add_argument(
        "--list", action="store_true", help="List available folders only"
    )

    parser.add_argument(
        "--raw-path",
        type=Path,
        default=project_root / "data" / "raw",
        help="Path to raw data folder (default: data/raw)",
    )

    args = parser.parse_args()

    # Validate raw path
    if not args.raw_path.exists():
        logger.error(f"❌ Raw data path not found: {args.raw_path}")
        sys.exit(1)

    # Create importer
    importer = BulkImporter(args.raw_path)

    try:
        # List folders only
        if args.list:
            folders = importer.get_available_folders()
            print(f"\n📂 Folders trong {args.raw_path}:")
            print("-" * 50)
            total_files = 0
            for name, count in folders:
                print(f"  📁 {name}: {count} files")
                total_files += count
            print("-" * 50)
            print(f"  📊 Total: {len(folders)} folders, {total_files} files")
            return

        # Import specific folder
        if args.folder:
            importer.run_folder(args.folder, dry_run=args.dry_run)
            return

        # Import all folders sequentially
        if args.all:
            folders = importer.get_available_folders()
            total_success = 0
            total_failed = 0

            print(f"\n🚀 Importing all {len(folders)} folders...")
            print("=" * 60)

            for i, (folder_name, file_count) in enumerate(folders, 1):
                print(f"\n📂 [{i}/{len(folders)}] {folder_name} ({file_count} files)")
                print("-" * 40)

                success = importer.run_folder(folder_name, dry_run=args.dry_run)

                if success:
                    total_success += 1
                else:
                    total_failed += 1

                # Reset stats for next folder
                importer.stats = {
                    "total_files": 0,
                    "processed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total_chunks": 0,
                    "errors": [],
                }

            print("\n" + "=" * 60)
            print(
                f"✅ ALL FOLDERS COMPLETE: {total_success} success, {total_failed} failed"
            )
            print("=" * 60)
            return

        # Interactive mode (default)
        interactive_mode(importer, dry_run=args.dry_run)

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  Import interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
