"""
DOCX Processing Pipeline cho văn bản đấu thầu

Pipeline tổng hợp:
DOCX → Extract → Clean → Parse Structure → Chunk → JSONL

Compatible với existing chunking system (OptimalLegalChunker)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Import local modules
from .docx_extractor import DocxExtractor, ExtractedContent
from src.preprocessing.cleaners.legal_cleaner import LegalDocumentCleaner
from .bidding_law_parser import BiddingLawParser, StructureNode
from .optimal_chunker import OptimalLegalChunker, LawChunk


class DocxProcessingPipeline:
    """
    End-to-end pipeline để xử lý DOCX files về đấu thầu
    """

    def __init__(
        self,
        max_chunk_size: int = 2000,
        min_chunk_size: int = 300,
        aggressive_clean: bool = False,
    ):
        """
        Args:
            max_chunk_size: Max size của chunk (chars)
            min_chunk_size: Min size của chunk (chars)
            aggressive_clean: Apply aggressive cleaning
        """
        self.extractor = DocxExtractor()
        self.cleaner = LegalDocumentCleaner()
        self.parser = BiddingLawParser()
        self.chunker = OptimalLegalChunker(
            max_chunk_size=max_chunk_size, min_chunk_size=min_chunk_size
        )
        self.aggressive_clean = aggressive_clean

    def process_single_file(
        self, docx_path: str | Path, output_dir: Optional[str | Path] = None
    ) -> Dict:
        """
        Process một file DOCX duy nhất

        Args:
            docx_path: Path đến .docx file
            output_dir: Directory để save outputs (JSON, JSONL, MD)

        Returns:
            Dict với processing results
        """
        docx_path = Path(docx_path)
        print(f"\n{'='*80}")
        print(f"PROCESSING: {docx_path.name}")
        print(f"{'='*80}\n")

        # Step 1: Extract từ DOCX
        print("📄 Step 1: Extracting from DOCX...")
        extracted = self.extractor.extract(docx_path)
        print(f"   ✅ Extracted {extracted.statistics['char_count']:,} chars")
        print(f"   ✅ Found {extracted.statistics.get('dieu_count', 0)} Điều")

        # Step 2: Clean text
        print("\n🧹 Step 2: Cleaning text...")
        cleaned_text = self.cleaner.clean(extracted.text, self.aggressive_clean)
        validation = self.cleaner.validate_cleaned_text(cleaned_text)
        print(f"   ✅ Cleaned to {validation['statistics']['char_count']:,} chars")
        if validation["warnings"]:
            print(f"   ⚠️ Warnings: {', '.join(validation['warnings'])}")

        # Step 3: Parse structure
        print("\n🏗️ Step 3: Parsing structure...")
        root_node = self.parser.parse(cleaned_text, extracted.metadata)
        structure_stats = self.parser.get_statistics(root_node)
        print(f"   ✅ Parsed structure:")
        for key, value in structure_stats.items():
            if value > 0:
                print(f"      - {key}: {value}")

        # Step 4: Prepare document for chunking
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

        # Step 6: Export outputs
        results = {
            "file_path": str(docx_path),
            "extracted": extracted,
            "cleaned_text": cleaned_text,
            "structure": root_node,
            "chunks": chunks,
            "statistics": {
                "extraction": extracted.statistics,
                "cleaning": validation,
                "structure": structure_stats,
                "chunking": chunk_stats,
            },
            "metadata": extracted.metadata,
        }

        if output_dir:
            print("\n💾 Step 6: Exporting outputs...")
            self._export_outputs(results, output_dir)

        print(f"\n{'='*80}")
        print("✅ PROCESSING COMPLETE!")
        print(f"{'='*80}\n")

        return results

    def process_batch(
        self, input_dir: str | Path, output_dir: str | Path, pattern: str = "*.docx"
    ) -> Dict:
        """
        Process batch nhiều files

        Args:
            input_dir: Directory chứa .docx files
            output_dir: Directory để save outputs
            pattern: File pattern (default: *.docx)

        Returns:
            Dict với batch processing results
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all matching files
        docx_files = list(input_dir.glob(pattern))
        print(f"\n🔍 Found {len(docx_files)} files to process\n")

        batch_results = {
            "processed": [],
            "failed": [],
            "statistics": {"total": len(docx_files), "success": 0, "failed": 0},
        }

        for docx_file in docx_files:
            try:
                # Create output subdir for this file
                file_output_dir = output_dir / docx_file.stem

                # Process
                result = self.process_single_file(docx_file, file_output_dir)

                batch_results["processed"].append(
                    {
                        "file": str(docx_file),
                        "status": "success",
                        "chunks": len(result["chunks"]),
                        "statistics": result["statistics"],
                    }
                )
                batch_results["statistics"]["success"] += 1

            except Exception as e:
                print(f"\n❌ Error processing {docx_file.name}: {str(e)}\n")
                batch_results["failed"].append(
                    {"file": str(docx_file), "error": str(e)}
                )
                batch_results["statistics"]["failed"] += 1

        # Export batch summary
        summary_file = output_dir / "batch_processing_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n📊 BATCH PROCESSING SUMMARY:")
        print(f"   Total files: {batch_results['statistics']['total']}")
        print(f"   Success: {batch_results['statistics']['success']}")
        print(f"   Failed: {batch_results['statistics']['failed']}")
        print(f"   Summary saved: {summary_file}")

        return batch_results

    def _convert_to_document_format(
        self, extracted: ExtractedContent, cleaned_text: str, root_node: StructureNode
    ) -> Dict:
        """
        Convert sang format compatible với OptimalLegalChunker

        Format:
        {
            "info": {...metadata...},
            "content": {"full_text": "..."},
            "structure": {...}
        }
        """
        # Get flat structure
        flat_structure = self.parser.get_flat_structure(root_node)

        return {
            "info": extracted.metadata,
            "content": {"full_text": cleaned_text},
            "structure": flat_structure,
            "statistics": extracted.statistics,
        }

    def _export_outputs(self, results: Dict, output_dir: str | Path):
        """Export multiple output formats"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(results["file_path"]).stem

        # 1. Export JSON (full structured data)
        json_file = output_dir / f"{filename}_structured.json"
        json_data = {
            "metadata": results["metadata"],
            "content": results["cleaned_text"],
            "structure": self.parser.to_json(results["structure"]),
            "statistics": results["statistics"],
            "processed_at": datetime.now().isoformat(),
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"   💾 JSON: {json_file}")

        # 2. Export JSONL (chunks for vector database)
        jsonl_file = output_dir / f"{filename}_chunks.jsonl"
        if hasattr(self.chunker, "export_chunks_to_jsonl"):
            self.chunker.export_chunks_to_jsonl(results["chunks"], str(jsonl_file))
        else:
            # Manual JSONL export
            with open(jsonl_file, "w", encoding="utf-8") as f:
                for i, chunk in enumerate(results["chunks"]):
                    chunk_dict = {
                        "chunk_id": i,
                        "text": chunk.text,
                        "metadata": chunk.metadata,
                        "level": chunk.level,
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

    def _generate_report(self, results: Dict) -> str:
        """Generate human-readable processing report"""
        lines = [
            "=" * 80,
            "DOCX PROCESSING REPORT",
            "=" * 80,
            "",
            f"File: {results['file_path']}",
            f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "METADATA:",
            "-" * 40,
        ]

        for key, value in results["metadata"].items():
            lines.append(f"  {key}: {value}")

        lines.extend(
            [
                "",
                "EXTRACTION STATISTICS:",
                "-" * 40,
            ]
        )

        for key, value in results["statistics"]["extraction"].items():
            lines.append(
                f"  {key}: {value:,}" if isinstance(value, int) else f"  {key}: {value}"
            )

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
            if isinstance(value, dict):
                lines.append(f"  {key}:")
                for k, v in value.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(
                    f"  {key}: {value:.0f}"
                    if isinstance(value, float)
                    else f"  {key}: {value}"
                )

        lines.extend(
            [
                "",
                "VALIDATION WARNINGS:",
                "-" * 40,
            ]
        )

        warnings = results["statistics"]["cleaning"].get("warnings", [])
        if warnings:
            for warning in warnings:
                lines.append(f"  ⚠️ {warning}")
        else:
            lines.append("  ✅ No warnings")

        lines.extend(["", "=" * 80])

        return "\n".join(lines)


# ============ USAGE EXAMPLE ============

if __name__ == "__main__":
    from pathlib import Path

    # Initialize pipeline
    pipeline = DocxProcessingPipeline(
        max_chunk_size=2000, min_chunk_size=300, aggressive_clean=False
    )

    # Example 1: Process single file
    docx_file = Path("data/raw/Luat chinh/Luat Dau thau 2023.docx")

    if docx_file.exists():
        output_dir = Path("data/processed")

        results = pipeline.process_single_file(docx_file, output_dir)

        print("\n✅ Single file processing complete!")
        print(f"   Chunks created: {len(results['chunks'])}")
        print(f"   Output directory: {output_dir}")
    else:
        print(f"❌ File not found: {docx_file}")

    # Example 2: Batch processing
    # input_dir = Path("data/raw/Luat chinh")
    # output_dir = Path("data/processed")
    #
    # if input_dir.exists():
    #     batch_results = pipeline.process_batch(input_dir, output_dir)
    #     print(f"\n✅ Batch processing complete!")
