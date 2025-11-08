"""
Circular Preprocessing Pipeline

Complete pipeline for processing Vietnamese Circular documents (Thông tư).
Handles extraction, cleaning, parsing, chunking, and metadata mapping.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Core components
from .extractors.circular_extractor import CircularExtractor, ExtractedContent
from .cleaners.circular_cleaner import CircularCleaner
from .parsers.circular_parser import CircularParser, StructureNode
from .metadata_mapper import CircularMetadataMapper

# Import chunker and other dependencies
from src.preprocessing.parsers.optimal_chunker import OptimalLegalChunker, LawChunk
from src.preprocessing.validators.hierarchy_schemas import CircularHierarchySchema


class CircularPreprocessingPipeline:
    """Complete preprocessing pipeline for Circular documents"""

    def __init__(
        self,
        chunk_size_range: tuple[int, int] = (300, 2000),
        validate_integrity: bool = False,
        chunking_strategy: str = "optimal_hybrid",
    ):
        """
        Initialize Circular preprocessing pipeline

        Args:
            chunk_size_range: Min and max chunk sizes in characters
            validate_integrity: Whether to run data integrity validation
            chunking_strategy: Chunking strategy to use
        """
        self.chunk_size_range = chunk_size_range
        self.validate_integrity = validate_integrity
        self.chunking_strategy = chunking_strategy

        # Initialize components
        self.extractor = CircularExtractor(preserve_formatting=True)
        self.cleaner = CircularCleaner()
        self.parser = CircularParser()
        self.chunker = OptimalLegalChunker(
            min_chunk_size=chunk_size_range[0],
            max_chunk_size=chunk_size_range[1],
            overlap_size=150,
        )
        self.mapper = CircularMetadataMapper()

        # Initialize integrity validator if needed
        if self.validate_integrity:
            try:
                from src.preprocessing.law_preprocessing.validators.integrity_validator import (
                    DataIntegrityValidator,
                )

                self.integrity_validator = DataIntegrityValidator()
            except ImportError:
                self.validate_integrity = False
                print("⚠️  Integrity validator not available - disabled")

    def process_single_file(self, docx_file: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Process single Circular DOCX file

        Args:
            docx_file: Path to input .docx file
            output_dir: Directory for output files

        Returns:
            Dictionary containing processing results and metadata
        """
        docx_file = Path(docx_file)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📄 Step 1: Extracting from DOCX...")
        print(f"📄 Extracting: {docx_file.name}")

        # Step 1: Extract content
        extracted = self.extractor.extract(docx_file)
        print(f"   ✅ Extracted {len(extracted.text):,} chars")
        if extracted.statistics.get("structure_elements", 0) > 0:
            print(
                f"   ✅ Found {extracted.statistics['structure_elements']} structure elements"
            )

        # Step 2: Clean text
        print(f"\n🧹 Step 2: Cleaning text...")
        cleaned_text = self.cleaner.clean(extracted.text, aggressive=False)
        cleaning_stats = self.cleaner.get_cleaning_stats(extracted.text, cleaned_text)
        print(f"   ✅ Cleaned to {len(cleaned_text):,} chars")
        if cleaning_stats["chars_removed"] > 0:
            print(
                f"   ✅ Removed {cleaning_stats['chars_removed']:,} chars ({cleaning_stats['reduction_percentage']:.1f}%)"
            )

        # Step 3: Parse structure
        print(f"\n🏗️ Step 3: Parsing structure...")
        root_node = self.parser.parse(cleaned_text)
        structure_summary = self.parser.get_structure_summary(root_node)
        print(f"   ✅ Parsed structure:")
        for struct_type, count in structure_summary["node_counts"].items():
            if struct_type != "circular_root" and count > 0:
                print(f"      - {struct_type}_count: {count}")
        print(f"      - total_nodes: {structure_summary['total_nodes']}")

        # Step 4: Prepare for chunking
        print(f"\n📦 Step 4: Preparing for chunking...")
        document = self._convert_to_document_format(extracted, cleaned_text, root_node)

        # Step 5: Chunk document
        print(f"\n✂️ Step 5: Chunking document...")
        chunks = self.chunker.optimal_chunk_document(document)

        # Get statistics
        if hasattr(self.chunker, "get_chunking_stats"):
            chunk_stats = self.chunker.get_chunking_stats(chunks)
            print(f"   ✅ Created {len(chunks)} chunks")
            print(f"   ✅ Avg size: {chunk_stats['avg_chunk_size']:.0f} chars")
            print(f"   ✅ Distribution: {chunk_stats['by_level']}")
        else:
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
        print(f"\n🗄️ Step 6: Mapping to DB schema...")
        db_chunks = self._map_chunks_to_db_schema(chunks, extracted.metadata)
        print(f"   ✅ Mapped {len(db_chunks)} chunks to DB schema")

        # Step 6.5: Data Integrity Check
        if self.validate_integrity and db_chunks:
            print(f"\n🔍 Step 6.5: Checking data integrity...")

            # Add chunk_content to db_chunks for validation
            db_chunks_with_content = []
            for i, db_chunk in enumerate(db_chunks):
                chunk_with_content = db_chunk.copy()
                chunk_with_content["chunk_content"] = chunks[i].text
                db_chunks_with_content.append(chunk_with_content)

            integrity_report = self.integrity_validator.validate(
                original_text=cleaned_text,
                processed_chunks=db_chunks_with_content,
                structure_tree=root_node,
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

        # Step 7: Export outputs
        print(f"\n💾 Step 7: Exporting outputs...")
        results = {
            "file_path": str(docx_file),
            "extracted": extracted,
            "cleaned_text": cleaned_text,
            "structure": root_node,
            "chunks": chunks,
            "db_chunks": db_chunks,
            "statistics": {
                **extracted.statistics,
                **cleaning_stats,
                **structure_summary,
                **chunk_stats,
            },
        }

        if self.validate_integrity and "integrity_report" in locals():
            results["integrity_report"] = integrity_report

        self._export_outputs(results, output_dir)

        print(
            f"\n================================================================================"
        )
        print(f"✅ PROCESSING COMPLETE!")
        print(
            f"================================================================================"
        )

        return results

    def _convert_to_document_format(
        self, extracted: ExtractedContent, text: str, structure: StructureNode
    ) -> Dict[str, Any]:
        """Convert extracted content to chunker-compatible format"""
        return {
            "content": text,  # OptimalLegalChunker expects 'content' field
            "metadata": extracted.metadata,
            "structure": structure,
            "tables": extracted.tables,
        }

    def _map_chunks_to_db_schema(
        self, chunks: List[Any], source_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Map chunks to DB schema using CircularMetadataMapper"""
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
                # chunk_data is now already in standardized format with text, metadata, etc.
                f.write(json.dumps(chunk_data, ensure_ascii=False) + "\n")
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
            "CIRCULAR PREPROCESSING REPORT",
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
                "PROCESSING STATISTICS:",
                "-" * 40,
            ]
        )

        stats = results["statistics"]
        for key, value in stats.items():
            if isinstance(value, dict):
                lines.append(f"  {key}:")
                for subkey, subval in value.items():
                    lines.append(f"    {subkey}: {subval}")
            else:
                lines.append(f"  {key}: {value}")

        # Add integrity report if available
        if "integrity_report" in results:
            integrity = results["integrity_report"]
            lines.extend(
                [
                    "",
                    "DATA INTEGRITY:",
                    "-" * 40,
                    f"  Coverage: {integrity.coverage_percentage:.1f}%",
                    f"  Checks passed: {integrity.passed_checks}/{integrity.total_checks}",
                    f"  Status: {'✅ PASS' if integrity.is_valid else '⚠️ WARNINGS'}",
                ]
            )

            if integrity.warnings:
                lines.append("  Warnings:")
                for warning in integrity.warnings:
                    lines.append(f"    - {warning}")

            if integrity.errors:
                lines.append("  Errors:")
                for error in integrity.errors:
                    lines.append(f"    - {error}")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics and configuration"""
        return {
            "chunk_size_range": self.chunk_size_range,
            "chunking_strategy": self.chunking_strategy,
            "validate_integrity": self.validate_integrity,
            "components": {
                "extractor": type(self.extractor).__name__,
                "cleaner": type(self.cleaner).__name__,
                "parser": type(self.parser).__name__,
                "chunker": type(self.chunker).__name__,
                "mapper": type(self.mapper).__name__,
            },
        }
