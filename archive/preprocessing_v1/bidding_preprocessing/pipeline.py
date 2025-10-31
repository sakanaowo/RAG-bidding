"""
Complete Bidding Document Preprocessing Pipeline

Integrates all components for processing Vietnamese bidding documents:
- Document extraction
- Text cleaning and normalization
- Structure parsing
- Content chunking
- Metadata mapping
- Data integrity validation
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .extractors import BiddingExtractor
from .cleaners import BiddingCleaner
from .parsers import BiddingParser
from .mappers import BiddingMetadataMapper

from .chunkers import SimpleBiddingChunker
from ..decree_preprocessing.validators.integrity_validator import DataIntegrityValidator


class BiddingPreprocessingPipeline:
    """
    Complete preprocessing pipeline for Vietnamese bidding documents

    Processes bidding documents through the following stages:
    1. Extraction: Extract content from document files
    2. Cleaning: Clean and normalize text content
    3. Parsing: Parse document structure and hierarchy
    4. Chunking: Split content into optimal chunks
    5. Mapping: Map chunks to standardized metadata format
    6. Validation: Validate data integrity and completeness
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        aggressive_cleaning: bool = False,
        validate_integrity: bool = True,
    ):
        """
        Initialize bidding preprocessing pipeline

        Args:
            chunk_size: Target size for content chunks
            chunk_overlap: Overlap between consecutive chunks
            aggressive_cleaning: Whether to apply aggressive text cleaning
            validate_integrity: Whether to validate data integrity
        """

        # Initialize components
        self.extractor = BiddingExtractor()
        self.cleaner = BiddingCleaner()
        self.parser = BiddingParser()
        self.chunker = SimpleBiddingChunker(
            chunk_size=chunk_size, overlap=chunk_overlap
        )
        self.mapper = BiddingMetadataMapper()

        # Configuration
        self.aggressive_cleaning = aggressive_cleaning
        self.validate_integrity = validate_integrity

        # Initialize validator if needed
        if self.validate_integrity:
            self.validator = DataIntegrityValidator()

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def process_file(self, file_path: str, output_dir: str = None) -> Dict[str, Any]:
        """
        Process a single bidding document file

        Args:
            file_path: Path to the bidding document file
            output_dir: Directory to save processed outputs

        Returns:
            Dictionary with processing results and statistics
        """

        self.logger.info(f"Starting bidding document processing: {file_path}")

        start_time = datetime.now()
        results = {
            "file_path": file_path,
            "status": "processing",
            "start_time": start_time.isoformat(),
            "stages": {},
            "final_chunks": [],
            "statistics": {},
            "validation": {},
            "errors": [],
        }

        try:
            # Stage 1: Extraction
            self.logger.info("Stage 1: Extracting content from document")
            from pathlib import Path

            extraction_result = self.extractor.extract(Path(file_path))

            # Extract content from ExtractedContent object
            raw_content = extraction_result.text
            extraction_metadata = extraction_result.metadata
            extraction_tables = extraction_result.tables
            extraction_stats = extraction_result.statistics

            results["stages"]["extraction"] = {
                "success": True,
                "content_length": len(raw_content),
                "metadata": extraction_metadata,
                "tables_count": len(extraction_tables),
                "statistics": extraction_stats,
                "bidding_type": extraction_metadata.get("bidding_type"),
            }

            # Stage 2: Cleaning
            self.logger.info("Stage 2: Cleaning and normalizing text")
            cleaned_content = self.cleaner.clean(
                raw_content, aggressive=self.aggressive_cleaning
            )

            cleaning_stats = self.cleaner.get_cleaning_stats(
                raw_content, cleaned_content
            )
            cleaning_validation = self.cleaner.validate_cleaning(
                raw_content, cleaned_content
            )

            if not cleaning_validation["is_valid"]:
                self.logger.warning("Cleaning validation failed")
                results["errors"].append(
                    "Text cleaning may have removed important content"
                )

            results["stages"]["cleaning"] = {
                "success": True,
                "stats": cleaning_stats,
                "validation": cleaning_validation,
            }

            # Stage 3: Parsing
            self.logger.info("Stage 3: Parsing document structure")
            parsing_result = self.parser.parse(
                cleaned_content, bidding_type=extraction_metadata.get("bidding_type")
            )

            results["stages"]["parsing"] = {
                "success": True,
                "sections_count": len(parsing_result["sections"]),
                "tables_count": len(parsing_result["tables"]),
                "structure_stats": parsing_result["structure_stats"],
                "metadata": parsing_result["metadata"],
            }

            # Stage 4: Chunking
            self.logger.info("Stage 4: Chunking content for processing")

            # Prepare content for chunking (combine sections)
            sections_text = self._prepare_content_for_chunking(
                parsing_result["sections"]
            )

            self.logger.info(f"Sections text length: {len(sections_text)}")
            self.logger.info(f"Sections text preview: {repr(sections_text[:200])}")

            # If no structured sections, use cleaned content directly
            if not sections_text or len(sections_text.strip()) < 50:
                self.logger.info("Using cleaned content directly for chunking")
                sections_text = cleaned_content

            # Create chunks using SimpleBiddingChunker
            document_dict = {
                "content": sections_text,
                "metadata": extraction_metadata,
                "doc_type": "bidding",
            }

            chunk_results = self.chunker.optimal_chunk_document(document_dict)
            self.logger.info(f"Chunks generated: {len(chunk_results)}")

            if not chunk_results:
                raise Exception("Chunking failed - no chunks generated")

            # Add parsing information to chunks
            enhanced_chunks = self._enhance_chunks_with_parsing(
                chunk_results, parsing_result, extraction_metadata
            )

            results["stages"]["chunking"] = {
                "success": True,
                "chunks_count": len(enhanced_chunks),
                "avg_chunk_size": sum(
                    len(c.get("content", "")) for c in enhanced_chunks
                )
                / len(enhanced_chunks),
                "chunking_stats": (
                    self.chunker.get_chunking_stats()
                    if hasattr(self.chunker, "get_chunking_stats")
                    else {}
                ),
            }

            # Stage 5: Metadata Mapping
            self.logger.info("Stage 5: Mapping metadata")

            document_metadata = {
                "source_file": os.path.basename(file_path),
                "file_path": file_path,
                "bidding_type": extraction_metadata.get("bidding_type"),
                "extraction_metadata": extraction_metadata,
                "parsing_metadata": parsing_result["metadata"],
            }

            final_chunks = self.mapper.map_chunks(enhanced_chunks, document_metadata)

            # Update total_chunks in each chunk's metadata
            for chunk in final_chunks:
                if "metadata" in chunk:
                    chunk["metadata"]["total_chunks"] = len(final_chunks)

            mapping_validation = self.mapper.validate_mapping(final_chunks)

            results["stages"]["mapping"] = {
                "success": True,
                "validation": mapping_validation,
            }

            results["final_chunks"] = final_chunks

            # Stage 6: Data Integrity Validation
            if self.validate_integrity:
                self.logger.info("Stage 6: Validating data integrity")

                validation_result = self.validator.validate(
                    original_text=cleaned_content,
                    processed_chunks=final_chunks,
                    structure_tree=parsing_result.get("sections"),
                    file_metadata=extraction_metadata,
                )

                # Convert IntegrityReport to dict for JSON serialization
                validation_dict = {
                    "is_valid": validation_result.is_valid,
                    "total_checks": validation_result.total_checks,
                    "passed_checks": validation_result.passed_checks,
                    "failed_checks": validation_result.failed_checks,
                    "original_char_count": validation_result.original_char_count,
                    "processed_char_count": validation_result.processed_char_count,
                    "coverage_percentage": validation_result.coverage_percentage,
                    "missing_sections": validation_result.missing_sections,
                    "duplicate_chunks": validation_result.duplicate_chunks,
                    "structure_preserved": validation_result.structure_preserved,
                    "hierarchy_complete": validation_result.hierarchy_complete,
                    "metadata_complete": validation_result.metadata_complete,
                    "warnings": validation_result.warnings,
                    "errors": validation_result.errors,
                    "issues": validation_result.warnings + validation_result.errors,
                }

                results["validation"] = validation_dict

                if not validation_result.is_valid:
                    self.logger.warning("Data integrity validation failed")
                    for issue in validation_dict["issues"]:
                        results["errors"].append(f"Integrity issue: {issue}")

            # Calculate final statistics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            results["statistics"] = {
                "processing_time_seconds": processing_time,
                "original_content_length": len(raw_content),
                "cleaned_content_length": len(cleaned_content),
                "final_chunks_count": len(final_chunks),
                "total_final_content_length": sum(
                    len(c.get("text", c.get("content", ""))) for c in final_chunks
                ),
                "average_chunk_size": (
                    sum(len(c.get("text", c.get("content", ""))) for c in final_chunks)
                    / len(final_chunks)
                    if final_chunks
                    else 0
                ),
                "content_coverage_ratio": (
                    sum(len(c.get("text", c.get("content", ""))) for c in final_chunks)
                    / len(cleaned_content)
                    if cleaned_content
                    else 0
                ),
            }

            # Save outputs if directory provided
            if output_dir:
                self._save_outputs(results, output_dir)

            results["status"] = "completed"
            results["end_time"] = end_time.isoformat()

            self.logger.info(
                f"Processing completed successfully in {processing_time:.2f} seconds"
            )

        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            results["status"] = "failed"
            results["error"] = str(e)
            results["end_time"] = datetime.now().isoformat()

            if "statistics" not in results:
                results["statistics"] = {}

        return results

    def process_directory(
        self, input_dir: str, output_dir: str, file_pattern: str = "*.doc*"
    ) -> Dict[str, Any]:
        """
        Process all bidding documents in a directory

        Args:
            input_dir: Directory containing bidding documents
            output_dir: Directory to save processed outputs
            file_pattern: File pattern to match (default: *.doc*)

        Returns:
            Dictionary with batch processing results
        """

        import glob

        self.logger.info(f"Starting batch processing: {input_dir}")

        # Find files
        search_pattern = os.path.join(input_dir, "**", file_pattern)
        files = glob.glob(search_pattern, recursive=True)

        if not files:
            return {
                "status": "completed",
                "files_found": 0,
                "files_processed": 0,
                "files_failed": 0,
                "results": {},
            }

        # Process each file
        batch_results = {
            "status": "processing",
            "files_found": len(files),
            "files_processed": 0,
            "files_failed": 0,
            "results": {},
            "errors": [],
            "start_time": datetime.now().isoformat(),
        }

        for file_path in files:
            try:
                self.logger.info(f"Processing file: {file_path}")

                # Create output subdirectory
                rel_path = os.path.relpath(file_path, input_dir)
                file_output_dir = os.path.join(output_dir, os.path.dirname(rel_path))
                os.makedirs(file_output_dir, exist_ok=True)

                # Process file
                result = self.process_file(file_path, file_output_dir)

                batch_results["results"][file_path] = result

                if result["status"] == "completed":
                    batch_results["files_processed"] += 1
                else:
                    batch_results["files_failed"] += 1
                    batch_results["errors"].append(
                        f"{file_path}: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {str(e)}")
                batch_results["files_failed"] += 1
                batch_results["errors"].append(f"{file_path}: {str(e)}")

        batch_results["status"] = "completed"
        batch_results["end_time"] = datetime.now().isoformat()

        # Calculate batch statistics
        successful_results = [
            r for r in batch_results["results"].values() if r["status"] == "completed"
        ]

        if successful_results:
            batch_results["statistics"] = {
                "total_chunks": sum(len(r["final_chunks"]) for r in successful_results),
                "average_processing_time": sum(
                    r["statistics"]["processing_time_seconds"]
                    for r in successful_results
                )
                / len(successful_results),
                "total_content_processed": sum(
                    r["statistics"]["original_content_length"]
                    for r in successful_results
                ),
            }

        self.logger.info(
            f"Batch processing completed: {batch_results['files_processed']} successful, {batch_results['files_failed']} failed"
        )

        return batch_results

    def _prepare_content_for_chunking(self, sections: List[Dict[str, Any]]) -> str:
        """Prepare parsed sections for chunking"""

        def sections_to_text(section_list, level=0):
            text_parts = []

            for section in section_list:
                # Add section header
                if section.get("title"):
                    header = f"{'#' * (level + 1)} {section.get('number', '')} {section['title']}".strip()
                    text_parts.append(header)

                # Add section content
                if section.get("content"):
                    text_parts.append(section["content"])

                # Add subsections recursively
                if section.get("subsections"):
                    subsection_text = sections_to_text(
                        section["subsections"], level + 1
                    )
                    if subsection_text:
                        text_parts.append(subsection_text)

            return "\n\n".join(text_parts)

        return sections_to_text(sections)

    def _enhance_chunks_with_parsing(
        self,
        chunks: List[Dict[str, Any]],
        parsing_result: Dict[str, Any],
        extraction_metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Enhance chunks with parsing information"""

        enhanced_chunks = []

        for chunk in chunks:
            enhanced_chunk = chunk.copy()

            # Add parsing metadata
            enhanced_chunk["parsed_sections"] = parsing_result.get("sections", [])
            enhanced_chunk["tables"] = parsing_result.get("tables", [])
            enhanced_chunk["parsing_metadata"] = parsing_result.get("metadata", {})
            enhanced_chunk["extraction_metadata"] = extraction_metadata

            enhanced_chunks.append(enhanced_chunk)

        return enhanced_chunks

    def _save_outputs(self, results: Dict[str, Any], output_dir: str):
        """Save processing outputs to files"""

        import json

        os.makedirs(output_dir, exist_ok=True)

        # Save chunks as JSONL
        chunks_file = os.path.join(output_dir, "chunks.jsonl")
        with open(chunks_file, "w", encoding="utf-8") as f:
            for chunk in results["final_chunks"]:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        # Save processing report
        report_file = os.path.join(output_dir, "processing_report.json")
        report_data = results.copy()
        report_data["final_chunks"] = []  # Don't duplicate chunk data in report

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Outputs saved to: {output_dir}")

    def get_pipeline_info(self) -> Dict[str, Any]:
        """Get information about pipeline configuration"""

        return {
            "pipeline_type": "bidding_preprocessing",
            "components": {
                "extractor": type(self.extractor).__name__,
                "cleaner": type(self.cleaner).__name__,
                "parser": type(self.parser).__name__,
                "chunker": type(self.chunker).__name__,
                "mapper": type(self.mapper).__name__,
            },
            "configuration": {
                "chunk_size": getattr(self.chunker, "chunk_size", None),
                "chunk_overlap": getattr(self.chunker, "chunk_overlap", None),
                "aggressive_cleaning": self.aggressive_cleaning,
                "validate_integrity": self.validate_integrity,
            },
            "supported_formats": ["doc", "docx"],
            "document_type": "bidding",
        }
