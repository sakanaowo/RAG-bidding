"""
Decree Preprocessing Pipeline - Main pipeline for decree documents

7-step processing flow:
1. Extract từ DOCX
2. Clean text
3. Parse structure
4. Chunk content
5. Map to DB schema
6. Validate
7. Export JSONL
"""

from pathlib import Path
from typing import List, Dict, Optional
import json

from ..base.base_pipeline import BaseDocumentPipeline
from .extractors.decree_extractor import DecreeExtractor, ExtractedContent
from .parsers.decree_parser import DecreeParser
from .cleaners.decree_cleaner import DecreeCleaner
from .metadata_mapper import DecreeMetadataMapper
from .validators.integrity_validator import DataIntegrityValidator

# Use existing legal chunker
from ...chunking.strategies.chunk_strategy import LegalDocumentChunker


class DecreePreprocessingPipeline(BaseDocumentPipeline):
    """
    Complete pipeline cho Nghị định preprocessing

    Simplified structure: Chương → Điều → Khoản → Điểm
    Validity: 2 years
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        output_dir: Optional[Path] = None,
        validate_integrity: bool = True,  # Enable integrity validation
    ):
        """
        Initialize decree pipeline

        Args:
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            output_dir: Output directory for processed files
            validate_integrity: Enable data integrity checks
        """
        self.extractor = DecreeExtractor(preserve_formatting=False)
        self.parser = DecreeParser()
        self.cleaner = DecreeCleaner()
        self.metadata_mapper = DecreeMetadataMapper()
        self.chunker = LegalDocumentChunker(
            strategy="hierarchical",
            max_chunk_size=chunk_size,
            overlap_size=chunk_overlap,
            keep_parent_context=True,
        )

        # Data integrity validator
        self.validate_integrity = validate_integrity
        if validate_integrity:
            self.integrity_validator = DataIntegrityValidator(
                min_coverage=0.85,  # Minimum 85% coverage
                max_duplication=0.05,  # Max 5% duplication
            )

        self.output_dir = output_dir or Path("data/processed/decrees")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        print(f"✅ DecreePreprocessingPipeline initialized")
        print(f"   Output: {self.output_dir}")
        if validate_integrity:
            print(f"   Integrity validation: ENABLED")

    def process(self, file_path: Path) -> List[Dict]:
        """
        Process decree file through full pipeline

        Args:
            file_path: Path to decree DOCX file

        Returns:
            List of DB-ready chunk records (25 fields each)
        """
        print(f"\n{'='*60}")
        print(f"Processing Decree: {file_path.name}")
        print(f"{'='*60}")

        # Step 1: Extract
        print("\n[1/7] Extracting content...")
        extracted = self.extractor.extract(file_path)
        print(f"   ✓ Extracted {len(extracted.text)} chars")

        # Step 2: Clean
        print("\n[2/7] Cleaning text...")
        cleaned_text = self.cleaner.clean(extracted.text)
        print(f"   ✓ Cleaned to {len(cleaned_text)} chars")

        # Step 3: Parse structure
        print("\n[3/7] Parsing structure...")
        structure_tree = self.parser.parse(cleaned_text, extracted.metadata)

        # Count nodes
        node_count = self._count_nodes(structure_tree)
        print(f"   ✓ Parsed {node_count} structure nodes")

        # Step 4: Chunk content
        print("\n[4/7] Chunking content...")

        # LegalDocumentChunker expects a document dict
        document_dict = {
            "content": {"full_text": cleaned_text},
            "info": extracted.metadata,
        }

        law_chunks = self.chunker.chunk_document(document_dict)

        # Convert LawChunk objects to simple text chunks
        chunks = [chunk.text for chunk in law_chunks]
        print(f"   ✓ Created {len(chunks)} chunks")

        # Step 5: Map to DB schema
        print("\n[5/7] Mapping to DB schema...")
        db_records = self._map_chunks_to_db(
            chunks=chunks,
            structure_tree=structure_tree,
            file_metadata=extracted.metadata,
            file_path=file_path,
        )
        print(f"   ✓ Mapped {len(db_records)} records")

        # Step 6: Validate
        print("\n[6/7] Validating records...")
        valid_records = [
            r for r in db_records if self.metadata_mapper.validate_record(r)
        ]
        print(f"   ✓ {len(valid_records)}/{len(db_records)} records valid")

        # Step 6.5: Data Integrity Check
        if self.validate_integrity and valid_records:
            print("\n[6.5/7] Checking data integrity...")
            integrity_report = self.integrity_validator.validate(
                original_text=cleaned_text,
                processed_chunks=valid_records,
                structure_tree=structure_tree,
                file_metadata=extracted.metadata,
            )

            print(f"   Coverage: {integrity_report.coverage_percentage:.1f}%")
            print(
                f"   Checks: {integrity_report.passed_checks}/{integrity_report.total_checks} passed"
            )

            if integrity_report.warnings:
                print(f"   ⚠️  {len(integrity_report.warnings)} warnings")
                for warning in integrity_report.warnings[:3]:
                    print(f"      - {warning}")

            if integrity_report.errors:
                print(f"   ❌ {len(integrity_report.errors)} errors")
                for error in integrity_report.errors[:3]:
                    print(f"      - {error}")

            if not integrity_report.is_valid:
                print(f"\n⚠️  WARNING: Data integrity issues detected!")
                print(integrity_report)
                # Continue processing but log the issues

        # Step 7: Export
        print("\n[7/7] Exporting JSONL...")
        output_file = self._export_jsonl(valid_records, file_path)
        print(f"   ✓ Exported to {output_file.name}")

        print(f"\n{'='*60}")
        print(f"✅ Decree processing complete: {len(valid_records)} chunks")
        print(f"{'='*60}\n")

        return valid_records

    def _count_nodes(self, node) -> int:
        """Count total nodes in structure tree"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _map_chunks_to_db(
        self,
        chunks: List,
        structure_tree,
        file_metadata: Dict,
        file_path: Path,
    ) -> List[Dict]:
        """
        Map chunks to DB schema with hierarchy info

        Args:
            chunks: List of text chunks from chunker
            structure_tree: Parsed structure tree
            file_metadata: Metadata từ extractor
            file_path: Source file path

        Returns:
            List of DB records
        """
        # Enhance metadata
        enhanced_metadata = file_metadata.copy()
        enhanced_metadata["filename"] = file_path.name
        enhanced_metadata["source_url"] = file_metadata.get(
            "source_url", f"file://{file_path.absolute()}"
        )

        # For now, simple mapping without hierarchy paths
        # TODO: Match chunks to structure nodes for accurate paths
        db_records = self.metadata_mapper.map_batch(
            chunks=chunks,  # Already strings from conversion above
            file_metadata=enhanced_metadata,
        )

        return db_records

    def _export_jsonl(self, records: List[Dict], file_path: Path) -> Path:
        """
        Export records to JSONL

        Args:
            records: List of DB records
            file_path: Original file path (for naming)

        Returns:
            Path to output JSONL file
        """
        # Generate output filename
        output_name = file_path.stem + "_processed.jsonl"
        output_path = self.output_dir / output_name

        # Write JSONL
        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return output_path

    def map_to_db_schema(self, processed_data: any) -> List[Dict]:
        """
        Required by BaseDocumentPipeline

        Map processed data to DB schema
        """
        # Already handled in process() method
        return processed_data

    def process_single_file(self, file_path: Path) -> List[Dict]:
        """
        Required by BaseDocumentPipeline

        Process single file
        """
        return self.process(file_path)

    def process_batch(self, file_paths: List[Path]) -> List[Dict]:
        """
        Required by BaseDocumentPipeline

        Process multiple files
        """
        all_records = []
        for file_path in file_paths:
            records = self.process(file_path)
            all_records.extend(records)
        return all_records

    def validate_output(self, output_data: List[Dict]) -> bool:
        """
        Required by BaseDocumentPipeline

        Validate output data
        """
        if not output_data:
            return False

        # Check all records have 25 fields
        return all(
            self.metadata_mapper.validate_record(record) for record in output_data
        )
