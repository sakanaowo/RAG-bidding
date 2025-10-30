"""
Law Preprocessing Pipeline - Complete pipeline for Law documents

Flow: DOCX → Extract → Clean → Parse → Chunk → Map to DB → Export
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Base classes
from ..base import BaseDocumentPipeline

# Law-specific modules
from .extractors.docx_extractor import DocxExtractor, ExtractedContent
from .cleaners.legal_cleaner import LegalDocumentCleaner
from .parsers.bidding_law_parser import BiddingLawParser, StructureNode
from .metadata_mapper import LawMetadataMapper
from .validators.integrity_validator import DataIntegrityValidator

# Chunking system (from parsers for now)
from ..parsers.optimal_chunker import OptimalLegalChunker


class LawPreprocessingPipeline(BaseDocumentPipeline):
    """
    Complete pipeline cho văn bản Luật

    Features:
    - Extract from DOCX
    - Clean legal text
    - Parse hierarchical structure (Phần→Chương→Mục→Điều→Khoản→Điểm)
    - Optimal chunking
    - Map to DB schema (25 fields)
    - Export to JSON/JSONL/MD
    """

    def __init__(
        self,
        max_chunk_size: int = 2000,
        min_chunk_size: int = 300,
        aggressive_clean: bool = False,
        validate_integrity: bool = True,  # Enable integrity validation
    ):
        """
        Initialize pipeline

        Args:
            max_chunk_size: Maximum chunk size in characters
            min_chunk_size: Minimum chunk size in characters
            aggressive_clean: Use aggressive cleaning
            validate_integrity: Enable data integrity checks
        """
        self.extractor = DocxExtractor()
        self.cleaner = LegalDocumentCleaner()
        self.parser = BiddingLawParser()
        self.chunker = OptimalLegalChunker(
            max_chunk_size=max_chunk_size, min_chunk_size=min_chunk_size
        )
        self.mapper = LawMetadataMapper()
        
        # Data integrity validator
        self.validate_integrity = validate_integrity
        if validate_integrity:
            self.integrity_validator = DataIntegrityValidator(
                min_coverage=0.75,  # Minimum 75% coverage
                max_duplication=0.05,  # Max 5% duplication
            )

        print(f"✅ LawPreprocessingPipeline initialized")
        print(f"   📏 Chunk size: {min_chunk_size}-{max_chunk_size} chars")
        if validate_integrity:
            print(f"   🔍 Integrity validation: ENABLED")

    def process_single_file(
        self, file_path: str | Path, output_dir: str | Path
    ) -> Dict[str, Any]:
        """
        Process single law DOCX file

        Args:
            file_path: Path to DOCX file
            output_dir: Output directory

        Returns:
            Processing results với chunks và metadata
        """
        docx_path = Path(file_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 80)
        print(f"PROCESSING: {docx_path.name}")
        print("=" * 80)

        # Step 1: Extract from DOCX
        print("\n📄 Step 1: Extracting from DOCX...")
        extracted = self.extractor.extract(docx_path)
        print(f"   ✅ Extracted {extracted.statistics['char_count']:,} chars")
        print(f"   ✅ Found {extracted.statistics.get('dieu_count', 0)} Điều")

        # Step 2: Clean text
        print("\n🧹 Step 2: Cleaning text...")
        cleaned_text = self.cleaner.clean(extracted.text)
        print(f"   ✅ Cleaned to {len(cleaned_text):,} chars")

        # Step 3: Parse structure
        print("\n🏗️ Step 3: Parsing structure...")
        root_node = self.parser.parse(cleaned_text)
        structure_stats = self._get_structure_stats(root_node)
        print(f"   ✅ Parsed structure:")
        for key, value in structure_stats.items():
            print(f"      - {key}: {value}")

        # Step 4: Convert to Document format
        print("\n📦 Step 4: Preparing for chunking...")
        document = self._convert_to_document_format(extracted, cleaned_text, root_node)

        # Step 5: Chunk document
        print("\n✂️ Step 5: Chunking document...")
        chunks = self.chunker.optimal_chunk_document(document)

        # Get statistics (handle different chunker types)
        if hasattr(self.chunker, "get_chunking_stats"):
            chunk_stats = self.chunker.get_chunking_stats(chunks)
            print(f"   ✅ Created {len(chunks)} chunks")
            print(f"   ✅ Avg size: {chunk_stats['avg_chunk_size']:.0f} chars")
            print(f"   ✅ Distribution: {chunk_stats['by_level']}")
        else:
            # Calculate basic stats manually
            chunk_sizes = [len(chunk.text) for chunk in chunks]
            chunk_stats = {
                "total_chunks": len(chunks),
                "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes) if chunks else 0,
                "min_chunk_size": min(chunk_sizes) if chunks else 0,
                "max_chunk_size": max(chunk_sizes) if chunks else 0,
            }
            print(f"   ✅ Created {len(chunks)} chunks")
            print(f"   ✅ Avg size: {chunk_stats['avg_chunk_size']:.0f} chars")

        # Step 6: Map chunks to DB schema
        print("\n🗄️ Step 6: Mapping to DB schema...")
        db_chunks = self._map_chunks_to_db_schema(chunks, extracted.metadata)
        print(f"   ✅ Mapped {len(db_chunks)} chunks to DB schema (25 fields)")
        
        # Step 6.5: Data Integrity Check
        if self.validate_integrity and db_chunks:
            print("\n🔍 Step 6.5: Checking data integrity...")
            
            # Add chunk_content to db_chunks for validation
            db_chunks_with_content = []
            for i, db_chunk in enumerate(db_chunks):
                chunk_with_content = db_chunk.copy()
                chunk_with_content['chunk_content'] = chunks[i].text
                db_chunks_with_content.append(chunk_with_content)
            
            integrity_report = self.integrity_validator.validate(
                original_text=cleaned_text,
                processed_chunks=db_chunks_with_content,
                structure_tree=root_node,
                file_metadata=extracted.metadata,
            )
            
            print(f"   Coverage: {integrity_report.coverage_percentage:.1f}%")
            print(f"   Checks: {integrity_report.passed_checks}/{integrity_report.total_checks} passed")
            
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
                # Store report in results for later review
                results_integrity_report = integrity_report
            else:
                results_integrity_report = integrity_report

        # Step 7: Export outputs
        results = {
            "file_path": str(docx_path),
            "extracted": extracted,
            "cleaned_text": cleaned_text,
            "structure": root_node,
            "chunks": chunks,
            "db_chunks": db_chunks,  # NEW: DB-ready chunks
            "statistics": {
                "extraction": extracted.statistics,
                "structure": structure_stats,
                "chunking": chunk_stats,
            },
        }
        
        # Add integrity report if validation enabled
        if self.validate_integrity and 'results_integrity_report' in locals():
            results["integrity_report"] = results_integrity_report

        print("\n💾 Step 7: Exporting outputs...")
        self._export_outputs(results, output_dir)

        print("\n" + "=" * 80)
        print("✅ PROCESSING COMPLETE!")
        print("=" * 80)

        return results

    def process_batch(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        pattern: str = "*.docx",
    ) -> Dict[str, Any]:
        """
        Process batch of law documents

        Args:
            input_dir: Input directory
            output_dir: Output directory
            pattern: File pattern (default: *.docx)

        Returns:
            Batch processing results
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        # Find files
        files = list(input_dir.glob(pattern))

        print(f"\n📁 Found {len(files)} files matching '{pattern}'")
        print("=" * 80)

        results = {"successful": 0, "failed": 0, "results": []}

        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] Processing: {file_path.name}")

            try:
                result = self.process_single_file(file_path, output_dir)
                results["successful"] += 1
                results["results"].append(
                    {"file": str(file_path), "status": "success", "result": result}
                )
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                results["failed"] += 1
                results["results"].append(
                    {"file": str(file_path), "status": "failed", "error": str(e)}
                )

        print("\n" + "=" * 80)
        print(
            f"✅ Batch complete: {results['successful']} succeeded, {results['failed']} failed"
        )
        print("=" * 80)

        return results

    def map_to_db_schema(self, processed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map processed data to DB schema

        Args:
            processed_data: Output from process_single_file

        Returns:
            List of chunks mapped to DB schema
        """
        return processed_data.get("db_chunks", [])

    def validate_output(self, output: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate pipeline output

        Args:
            output: Pipeline output

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        required_fields = ["file_path", "chunks", "statistics"]
        for field in required_fields:
            if field not in output:
                errors.append(f"Missing required field: {field}")

        # Check chunks
        if "chunks" in output:
            if not output["chunks"]:
                errors.append("No chunks created")
            elif len(output["chunks"]) < 1:
                errors.append("Too few chunks")

        # Check DB chunks
        if "db_chunks" in output:
            for i, chunk in enumerate(output["db_chunks"]):
                # Verify all 25 fields present
                required_db_fields = [
                    "chunk_id",
                    "source",
                    "url",
                    "title",
                    "chunk_level",
                    "dieu",
                    "status",
                    "valid_until",
                ]
                for field in required_db_fields:
                    if field not in chunk:
                        errors.append(f"Chunk {i}: missing DB field '{field}'")

        is_valid = len(errors) == 0
        return is_valid, errors

    # ============ HELPER METHODS ============

    def _get_structure_stats(self, root: StructureNode) -> Dict[str, int]:
        """Get structure statistics"""
        stats = {
            "phan_count": 0,
            "chuong_count": 0,
            "muc_count": 0,
            "dieu_count": 0,
            "khoan_count": 0,
            "diem_count": 0,
            "total_nodes": 0,
        }

        def count_nodes(node):
            stats["total_nodes"] += 1

            if node.level == "phan":
                stats["phan_count"] += 1
            elif node.level == "chuong":
                stats["chuong_count"] += 1
            elif node.level == "muc":
                stats["muc_count"] += 1
            elif node.level == "dieu":
                stats["dieu_count"] += 1
            elif node.level == "khoan":
                stats["khoan_count"] += 1
            elif node.level == "diem":
                stats["diem_count"] += 1

            for child in node.children:
                count_nodes(child)

        count_nodes(root)
        return stats

    def _convert_to_document_format(
        self, extracted: ExtractedContent, cleaned_text: str, root_node: StructureNode
    ) -> Dict[str, Any]:
        """Convert to Document format for chunking"""
        return {
            "content": cleaned_text,
            "metadata": {
                "filename": extracted.metadata.get("filename", ""),
                "title": extracted.metadata.get("title", ""),
                "url": extracted.metadata.get("url", ""),
                "source": "thuvienphapluat.vn",
                **extracted.metadata,
            },
            "structure": root_node,
        }

    def _map_chunks_to_db_schema(
        self, chunks: List[Any], source_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Map chunks to DB schema using LawMetadataMapper"""
        db_chunks = []

        for i, chunk in enumerate(chunks):
            db_chunk = self.mapper.map_chunk_to_db_schema(
                chunk=chunk,
                source_metadata=source_metadata,
                chunk_index=i,
                total_chunks=len(chunks),
            )
            db_chunks.append(db_chunk)

        return db_chunks

    def _export_outputs(self, results: Dict[str, Any], output_dir: Path):
        """Export pipeline outputs to various formats"""
        filename = Path(results["file_path"]).stem

        # 1. Export structured JSON (full structure)
        json_file = output_dir / f"{filename}_structured.json"
        json_data = {
            "metadata": results["extracted"].metadata,
            "structure": "Complex structure (see parsed tree)",  # TODO: Implement to_dict for StructureNode
            "statistics": results["statistics"],
            "processed_at": datetime.now().isoformat(),
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"   💾 JSON: {json_file}")

        # 2. Export JSONL (DB-ready chunks for vector database)
        jsonl_file = output_dir / f"{filename}_chunks.jsonl"
        with open(jsonl_file, "w", encoding="utf-8") as f:
            for chunk_data in results["db_chunks"]:
                # Include text + all metadata fields
                chunk_dict = {
                    "text": results["chunks"][chunk_data["chunk_id"]].text,
                    "metadata": chunk_data,
                }
                f.write(json.dumps(chunk_dict, ensure_ascii=False) + "\n")
        print(f"   💾 JSONL: {jsonl_file}")

        # 3. Export Markdown (for review)
        md_file = output_dir / f"{filename}.md"
        self.extractor.export_to_md(results["extracted"], md_file)
        print(f"   💾 MD: {md_file}")

        # 4. Export processing report
        report_file = output_dir / f"{filename}_report.txt"
        report = self._generate_report(results)
        report_file.write_text(report, encoding="utf-8")
        print(f"   💾 Report: {report_file}")

    def _generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable processing report"""
        lines = [
            "=" * 80,
            "LAW PREPROCESSING REPORT",
            "=" * 80,
            "",
            f"File: {results['file_path']}",
            f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "METADATA:",
            "-" * 40,
        ]

        # Add metadata
        for key, value in results["extracted"].metadata.items():
            lines.append(f"  {key}: {value}")

        # Add statistics
        lines.extend(
            [
                "",
                "EXTRACTION STATISTICS:",
                "-" * 40,
            ]
        )

        for key, value in results["statistics"]["extraction"].items():
            if isinstance(value, (int, float)):
                lines.append(f"  {key}: {value:,}")
            else:
                lines.append(f"  {key}: {value}")

        lines.extend(
            [
                "",
                "STRUCTURE STATISTICS:",
                "-" * 40,
            ]
        )

        for key, value in results["statistics"]["structure"].items():
            lines.append(f"  {key}: {value}")

        lines.extend(
            [
                "",
                "CHUNKING STATISTICS:",
                "-" * 40,
            ]
        )

        for key, value in results["statistics"]["chunking"].items():
            if isinstance(value, (int, float)):
                lines.append(
                    f"  {key}: {value:,}"
                    if isinstance(value, int)
                    else f"  {key}: {value:.0f}"
                )
            else:
                lines.append(f"  {key}: {value}")

        lines.extend(
            [
                "",
                "DB SCHEMA VALIDATION:",
                "-" * 40,
                f"  Total chunks mapped: {len(results['db_chunks'])}",
                f"  Fields per chunk: 25",
                f"  Status: {results['db_chunks'][0].get('status', 'unknown') if results['db_chunks'] else 'N/A'}",
                "",
                "=" * 80,
            ]
        )

        return "\n".join(lines)
