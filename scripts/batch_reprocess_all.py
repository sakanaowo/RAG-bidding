#!/usr/bin/env python3
"""
Batch Re-Processing Script for Phase 4
Processes all raw documents with unified pipeline (UniversalChunk format)

Author: Development Team
Date: 2025-11-01
Phase: 4 - Batch Re-Processing
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.loaders.docx_loader import DocxLoader
from src.preprocessing.loaders.doc_loader import DocLoader
from src.preprocessing.base.models import ProcessedDocument
from src.chunking.chunk_factory import create_chunker
from src.chunking.base_chunker import UniversalChunk

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/outputs/batch_reprocess.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for batch processing"""

    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    total_chunks: int = 0
    skipped_files: int = 0
    start_time: float = 0
    end_time: float = 0

    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0

    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100


@dataclass
class DocumentMapping:
    """Mapping of raw file paths to document types"""

    path: str
    document_type: str
    category: str


class BatchProcessor:
    """Batch processor for all raw documents"""

    # Document type mapping based on directory structure
    TYPE_MAPPING = {
        "Luat chinh": "law",
        "Nghi dinh": "decree",
        "Thong tu": "circular",
        "Quyet dinh": "decision",
        "Ho so moi thau": "bidding",
        "Mau bao cao": "bidding",
    }

    def __init__(
        self,
        raw_dir: Path,
        output_dir: Path,
        max_workers: int = 4,
        batch_size: int = 10,
    ):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.batch_size = batch_size

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "chunks").mkdir(exist_ok=True)
        (self.output_dir / "metadata").mkdir(exist_ok=True)

        # Statistics
        self.stats = ProcessingStats()

        # Initialize loaders
        self.docx_loader = DocxLoader()
        self.doc_loader = DocLoader()

        # Log .doc support status
        if self.doc_loader.can_process():
            logger.info("✅ .doc file support enabled")
        else:
            logger.warning(
                "⚠️  .doc file support disabled (install antiword or libreoffice)"
            )

    def discover_documents(self) -> List[DocumentMapping]:
        """Discover all documents in raw directory"""
        logger.info("🔍 Discovering documents...")

        documents = []

        for root, dirs, files in os.walk(self.raw_dir):
            for file in files:
                # Only process DOCX and DOC files
                if not (file.endswith(".docx") or file.endswith(".doc")):
                    continue

                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.raw_dir)

                # Determine document type from path
                doc_type = self._determine_document_type(rel_path)
                category = self._get_category(rel_path)

                documents.append(
                    DocumentMapping(
                        path=str(file_path), document_type=doc_type, category=category
                    )
                )

        logger.info(f"📊 Found {len(documents)} documents")
        self._print_discovery_summary(documents)

        return documents

    def _determine_document_type(self, rel_path: Path) -> str:
        """Determine document type from relative path"""
        parts = rel_path.parts

        if len(parts) == 0:
            return "unknown"

        # Check first directory
        first_dir = parts[0]

        for key, doc_type in self.TYPE_MAPPING.items():
            if key in first_dir:
                return doc_type

        return "unknown"

    def _get_category(self, rel_path: Path) -> str:
        """Get category/subcategory from path"""
        parts = rel_path.parts

        if len(parts) >= 2:
            return parts[1]  # Subcategory
        elif len(parts) >= 1:
            return parts[0]  # Main category

        return "general"

    def _print_discovery_summary(self, documents: List[DocumentMapping]):
        """Print summary of discovered documents"""
        from collections import Counter

        type_counts = Counter(doc.document_type for doc in documents)

        logger.info("\n" + "=" * 80)
        logger.info("📋 DOCUMENT INVENTORY")
        logger.info("=" * 80)

        for doc_type, count in type_counts.most_common():
            logger.info(f"   {doc_type:15s}: {count:3d} files")

        logger.info("=" * 80 + "\n")

    def process_single_document(
        self, doc_mapping: DocumentMapping
    ) -> Tuple[bool, Optional[List[UniversalChunk]], Optional[str]]:
        """
        Process a single document through the pipeline

        Returns:
            (success, chunks, error_message)
        """
        try:
            file_path = Path(doc_mapping.path)

            # Step 1: Extract content
            try:
                # Choose loader based on file extension
                if file_path.suffix.lower() == ".doc":
                    # Old Word format - use DocLoader
                    if not self.doc_loader.can_process():
                        return (
                            False,
                            None,
                            "Cannot process .doc files (install antiword or libreoffice)",
                        )

                    content, doc_metadata = self.doc_loader.load(str(file_path))
                    extraction_method = doc_metadata.get(
                        "extraction_method", "doc_loader"
                    )
                else:
                    # Modern DOCX format - use DocxLoader
                    raw_content = self.docx_loader.load(str(file_path))
                    content = raw_content.text
                    extraction_method = "docx_loader"

            except Exception as e:
                return False, None, f"Extraction failed: {str(e)}"

            if not content or len(content.strip()) < 50:
                return False, None, "Empty or too short content"

            # Step 2: Create ProcessedDocument
            processed_doc = ProcessedDocument(
                metadata={
                    "source_file": file_path.name,
                    "document_type": doc_mapping.document_type,
                    "category": doc_mapping.category,
                    "file_path": str(file_path),
                    "processed_at": datetime.now().isoformat(),
                    "extraction_method": extraction_method,  # Track extraction method
                },
                content={
                    "full_text": content,
                },
            )

            # Step 3: Select and run chunker
            try:
                chunker = create_chunker(document_type=doc_mapping.document_type)
            except Exception as e:
                return False, None, f"Chunker creation failed: {str(e)}"

            try:
                chunks = chunker.chunk(processed_doc)
            except Exception as e:
                return False, None, f"Chunking failed: {str(e)}"

            if not chunks:
                return False, None, "No chunks generated"

            return True, chunks, None

        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"

    def save_chunks(
        self, chunks: List[UniversalChunk], doc_mapping: DocumentMapping
    ) -> bool:
        """Save chunks to JSONL file"""
        try:
            # Create safe filename
            safe_name = Path(doc_mapping.path).stem.replace(" ", "_")
            output_file = self.output_dir / "chunks" / f"{safe_name}.jsonl"

            with open(output_file, "w", encoding="utf-8") as f:
                for chunk in chunks:
                    chunk_dict = asdict(chunk)
                    f.write(json.dumps(chunk_dict, ensure_ascii=False) + "\n")

            # Save metadata
            metadata_file = self.output_dir / "metadata" / f"{safe_name}.json"
            metadata = {
                "source_file": doc_mapping.path,
                "document_type": doc_mapping.document_type,
                "category": doc_mapping.category,
                "chunk_count": len(chunks),
                "output_file": str(output_file),
                "processed_at": datetime.now().isoformat(),
            }

            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to save chunks: {e}")
            return False

    def process_batch(
        self, documents: List[DocumentMapping], show_progress: bool = True
    ) -> ProcessingStats:
        """Process a batch of documents"""
        self.stats = ProcessingStats(total_files=len(documents), start_time=time.time())

        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 STARTING BATCH PROCESSING")
        logger.info(f"{'='*80}")
        logger.info(f"Documents: {len(documents)}")
        logger.info(f"Max workers: {self.max_workers}")
        logger.info(f"{'='*80}\n")

        # Process documents
        for i, doc_mapping in enumerate(documents, 1):
            if show_progress:
                self._print_progress(i, len(documents), doc_mapping)

            success, chunks, error_msg = self.process_single_document(doc_mapping)

            if success and chunks:
                # Save chunks
                if self.save_chunks(chunks, doc_mapping):
                    self.stats.processed_files += 1
                    self.stats.total_chunks += len(chunks)

                    if show_progress:
                        logger.info(f"   ✅ Success: {len(chunks)} chunks")
                else:
                    self.stats.failed_files += 1
                    if show_progress:
                        logger.error(f"   ❌ Failed to save chunks")
            else:
                self.stats.failed_files += 1
                if show_progress:
                    logger.error(f"   ❌ Failed: {error_msg}")

        self.stats.end_time = time.time()

        return self.stats

    def _print_progress(self, current: int, total: int, doc: DocumentMapping):
        """Print processing progress"""
        percentage = (current / total) * 100
        logger.info(
            f"\n[{current}/{total}] ({percentage:.1f}%) Processing {doc.document_type}: {Path(doc.path).name}"
        )

    def generate_report(self) -> str:
        """Generate processing report"""
        report = []
        report.append("\n" + "=" * 80)
        report.append("📊 BATCH PROCESSING REPORT")
        report.append("=" * 80)
        report.append(f"Total Files:      {self.stats.total_files}")
        report.append(f"Processed:        {self.stats.processed_files}")
        report.append(f"Failed:           {self.stats.failed_files}")
        report.append(f"Skipped:          {self.stats.skipped_files}")
        report.append(f"Total Chunks:     {self.stats.total_chunks}")
        report.append(f"Success Rate:     {self.stats.success_rate():.1f}%")
        report.append(f"Duration:         {self.stats.duration():.1f}s")

        if self.stats.processed_files > 0:
            avg_chunks = self.stats.total_chunks / self.stats.processed_files
            throughput = self.stats.processed_files / self.stats.duration()
            report.append(f"Avg Chunks/File:  {avg_chunks:.1f}")
            report.append(f"Throughput:       {throughput:.2f} files/sec")

        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, report: str):
        """Save report to file"""
        report_file = self.output_dir / "batch_processing_report.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")

        logger.info(f"\n📄 Report saved to: {report_file}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Batch re-process all raw documents")
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Directory containing raw documents",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Output directory for processed chunks",
    )
    parser.add_argument(
        "--max-workers", type=int, default=1, help="Maximum number of parallel workers"
    )
    parser.add_argument(
        "--doc-type",
        type=str,
        choices=["law", "decree", "circular", "decision", "bidding", "all"],
        default="all",
        help="Process only specific document type",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Discover documents but don't process"
    )

    args = parser.parse_args()

    # Initialize processor
    processor = BatchProcessor(
        raw_dir=args.raw_dir, output_dir=args.output_dir, max_workers=args.max_workers
    )

    # Discover documents
    all_documents = processor.discover_documents()

    # Filter by type if specified
    if args.doc_type != "all":
        documents = [doc for doc in all_documents if doc.document_type == args.doc_type]
        logger.info(f"🔍 Filtered to {len(documents)} {args.doc_type} documents")
    else:
        documents = all_documents

    if args.dry_run:
        logger.info("🏁 Dry run complete. Exiting.")
        return 0

    # Confirm before processing
    print(f"\n⚠️  About to process {len(documents)} documents.")
    response = input("Continue? [y/N]: ")

    if response.lower() != "y":
        logger.info("❌ Cancelled by user")
        return 1

    # Process documents
    stats = processor.process_batch(documents)

    # Generate and save report
    report = processor.generate_report()
    logger.info(report)
    processor.save_report(report)

    # Return exit code
    if stats.failed_files == 0:
        logger.info("\n🎉 ALL DOCUMENTS PROCESSED SUCCESSFULLY!")
        return 0
    else:
        logger.warning(f"\n⚠️  Processing completed with {stats.failed_files} failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())
