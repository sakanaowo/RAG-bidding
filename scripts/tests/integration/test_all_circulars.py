#!/usr/bin/env python3
"""
Test All Circular Files

Test the circular preprocessing pipeline with all available circular documents
to identify edge cases and error patterns.
"""

import os
import sys
from pathlib import Path
import traceback
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.preprocessing.circular_preprocessing import CircularPreprocessingPipeline


def test_all_circular_files():
    """Test circular preprocessing pipeline with all circular documents"""

    # Configuration
    raw_data_dir = project_root / "data" / "raw" / "Thong tu"
    output_dir = project_root / "data" / "processed" / "circular_batch_test"

    print("=" * 80)
    print("TESTING ALL CIRCULAR DOCUMENTS")
    print("=" * 80)
    print(f"Raw data: {raw_data_dir}")
    print(f"Output: {output_dir}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Find all DOCX files
    docx_files = list(raw_data_dir.glob("*.docx"))

    if not docx_files:
        print(f"❌ No .docx files found in {raw_data_dir}")
        return False

    print(f"✅ Found {len(docx_files)} DOCX files:")
    for i, docx_file in enumerate(docx_files, 1):
        size_mb = docx_file.stat().st_size / (1024 * 1024)
        print(f"  {i}. {docx_file.name} ({size_mb:.1f} MB)")

    # Initialize pipeline once
    print(f"\n📦 Initializing Circular Preprocessing Pipeline...")
    pipeline = CircularPreprocessingPipeline(
        chunk_size_range=(300, 2000),
        validate_integrity=True,
        chunking_strategy="optimal_hybrid",
    )
    print("✅ Pipeline initialized\n")

    # Results tracking
    results_summary = {
        "total_files": len(docx_files),
        "successful": 0,
        "failed": 0,
        "warnings": 0,
        "files": [],
        "errors": [],
        "statistics": {
            "total_chunks": 0,
            "total_chars": 0,
            "avg_chunk_size": 0,
            "coverage_scores": [],
            "integrity_issues": 0,
        },
    }

    # Process each file
    for i, docx_file in enumerate(docx_files, 1):
        print("=" * 60)
        print(f"PROCESSING FILE {i}/{len(docx_files)}: {docx_file.name}")
        print("=" * 60)

        file_result = {
            "filename": docx_file.name,
            "file_size_mb": docx_file.stat().st_size / (1024 * 1024),
            "status": "unknown",
            "chunks": 0,
            "characters": 0,
            "coverage": 0.0,
            "warnings": [],
            "errors": [],
            "processing_time": 0,
        }

        start_time = datetime.now()

        try:
            # Process document
            results = pipeline.process_single_file(docx_file, output_dir)

            # Extract statistics
            coverage = 0.0
            if "integrity_report" in results:
                coverage = results["integrity_report"].coverage_percentage

            file_result.update(
                {
                    "status": "success",
                    "chunks": len(results["chunks"]),
                    "characters": len(results["cleaned_text"]),
                    "coverage": coverage,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                }
            )

            # Check for warnings
            if "integrity_report" in results:
                integrity = results["integrity_report"]
                if hasattr(integrity, "warnings") and integrity.warnings:
                    file_result["warnings"] = integrity.warnings
                    results_summary["warnings"] += 1
                if hasattr(integrity, "errors") and integrity.errors:
                    file_result["errors"] = integrity.errors
                    results_summary["statistics"]["integrity_issues"] += 1
                if hasattr(integrity, "is_valid") and not integrity.is_valid:
                    file_result["status"] = "success_with_warnings"

            results_summary["successful"] += 1
            results_summary["statistics"]["total_chunks"] += file_result["chunks"]
            results_summary["statistics"]["total_chars"] += file_result["characters"]
            results_summary["statistics"]["coverage_scores"].append(
                file_result["coverage"]
            )

            print(f"\n✅ SUCCESS: {docx_file.name}")
            print(f"   Chunks: {file_result['chunks']}")
            print(f"   Characters: {file_result['characters']:,}")
            print(f"   Coverage: {file_result['coverage']:.1f}%")
            print(f"   Time: {file_result['processing_time']:.1f}s")

            if file_result["warnings"]:
                print(f"   ⚠️  Warnings: {len(file_result['warnings'])}")
                for warning in file_result["warnings"][:2]:
                    print(f"      - {warning}")

        except Exception as e:
            file_result.update(
                {
                    "status": "failed",
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "errors": [str(e)],
                }
            )

            results_summary["failed"] += 1
            results_summary["errors"].append(
                {
                    "file": docx_file.name,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )

            print(f"\n❌ FAILED: {docx_file.name}")
            print(f"   Error: {str(e)}")
            print(f"   Time: {file_result['processing_time']:.1f}s")

            # Print short traceback for debugging
            print(f"   Traceback (last 3 lines):")
            tb_lines = traceback.format_exc().strip().split("\n")
            for line in tb_lines[-3:]:
                print(f"      {line}")

        results_summary["files"].append(file_result)
        print()

    # Generate summary report
    print("=" * 80)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 80)

    print(f"📊 OVERALL RESULTS:")
    print(f"   Total files: {results_summary['total_files']}")
    print(
        f"   Successful: {results_summary['successful']} ({results_summary['successful']/results_summary['total_files']*100:.1f}%)"
    )
    print(
        f"   Failed: {results_summary['failed']} ({results_summary['failed']/results_summary['total_files']*100:.1f}%)"
    )
    print(
        f"   With warnings: {results_summary['warnings']} ({results_summary['warnings']/results_summary['total_files']*100:.1f}%)"
    )

    if results_summary["successful"] > 0:
        stats = results_summary["statistics"]
        stats["avg_chunk_size"] = (
            stats["total_chars"] / stats["total_chunks"]
            if stats["total_chunks"] > 0
            else 0
        )
        avg_coverage = (
            sum(stats["coverage_scores"]) / len(stats["coverage_scores"])
            if stats["coverage_scores"]
            else 0
        )

        print(f"\n📈 AGGREGATED STATISTICS:")
        print(f"   Total chunks: {stats['total_chunks']:,}")
        print(f"   Total characters: {stats['total_chars']:,}")
        print(f"   Average chunk size: {stats['avg_chunk_size']:.0f} chars")
        print(f"   Average coverage: {avg_coverage:.1f}%")
        print(f"   Files with integrity issues: {stats['integrity_issues']}")

    # Show file-by-file results
    print(f"\n📋 FILE-BY-FILE RESULTS:")
    for file_result in results_summary["files"]:
        status_icon = (
            "✅"
            if file_result["status"] == "success"
            else "⚠️" if "warning" in file_result["status"] else "❌"
        )
        print(f"   {status_icon} {file_result['filename']}")
        print(
            f"      Size: {file_result['file_size_mb']:.1f}MB | Chunks: {file_result['chunks']} | Coverage: {file_result['coverage']:.1f}% | Time: {file_result['processing_time']:.1f}s"
        )

        if file_result["warnings"]:
            print(f"      Warnings: {len(file_result['warnings'])}")
        if file_result["errors"]:
            print(f"      Errors: {len(file_result['errors'])}")

    # Show error details if any
    if results_summary["errors"]:
        print(f"\n🚨 ERROR DETAILS:")
        for error_info in results_summary["errors"]:
            print(f"   File: {error_info['file']}")
            print(f"   Error: {error_info['error']}")
            print(f"   Full traceback saved to logs")
            print()

    # Save detailed report
    report_file = (
        output_dir
        / f"batch_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("CIRCULAR PREPROCESSING BATCH REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total files: {results_summary['total_files']}\n")
        f.write(f"Successful: {results_summary['successful']}\n")
        f.write(f"Failed: {results_summary['failed']}\n\n")

        f.write("FILE RESULTS:\n")
        f.write("-" * 30 + "\n")
        for file_result in results_summary["files"]:
            f.write(f"\nFile: {file_result['filename']}\n")
            f.write(f"Status: {file_result['status']}\n")
            f.write(f"Chunks: {file_result['chunks']}\n")
            f.write(f"Characters: {file_result['characters']:,}\n")
            f.write(f"Coverage: {file_result['coverage']:.1f}%\n")
            f.write(f"Processing time: {file_result['processing_time']:.1f}s\n")

            if file_result["warnings"]:
                f.write("Warnings:\n")
                for warning in file_result["warnings"]:
                    f.write(f"  - {warning}\n")

            if file_result["errors"]:
                f.write("Errors:\n")
                for error in file_result["errors"]:
                    f.write(f"  - {error}\n")

        if results_summary["errors"]:
            f.write(f"\n\nERROR TRACEBACKS:\n")
            f.write("-" * 30 + "\n")
            for error_info in results_summary["errors"]:
                f.write(f"\nFile: {error_info['file']}\n")
                f.write(f"Error: {error_info['error']}\n")
                f.write("Traceback:\n")
                f.write(error_info["traceback"])
                f.write("\n" + "-" * 50 + "\n")

    print(f"\n💾 Detailed report saved: {report_file}")

    # Return success if no failures
    return results_summary["failed"] == 0


if __name__ == "__main__":
    success = test_all_circular_files()

    if success:
        print(f"\n" + "=" * 80)
        print("✅ ALL CIRCULAR FILES PROCESSED SUCCESSFULLY!")
        print("=" * 80)
        sys.exit(0)
    else:
        print(f"\n" + "=" * 80)
        print("⚠️  SOME FILES FAILED - CHECK ERRORS ABOVE")
        print("=" * 80)
        sys.exit(1)
