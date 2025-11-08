#!/usr/bin/env python3
"""
Test script for bidding document preprocessing pipeline

Tests the complete bidding document preprocessing pipeline with sample documents.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.preprocessing.bidding_preprocessing import BiddingPreprocessingPipeline


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("bidding_preprocessing_test.log"),
        ],
    )


def test_single_bidding_document():
    """Test processing a single bidding document"""

    print("=== Testing Single Bidding Document Processing ===")

    # Initialize pipeline
    pipeline = BiddingPreprocessingPipeline(
        chunk_size=1000,
        chunk_overlap=200,
        aggressive_cleaning=False,
        validate_integrity=True,
    )

    # Print pipeline info
    pipeline_info = pipeline.get_pipeline_info()
    print(f"Pipeline: {pipeline_info['pipeline_type']}")
    print(f"Components: {list(pipeline_info['components'].values())}")

    # Test with bidding documents
    bidding_dir = Path("/home/sakana/Code/RAG-bidding/data/raw/Ho so moi thau")

    if not bidding_dir.exists():
        print(f"❌ Bidding documents directory not found: {bidding_dir}")
        return False

    # Find first bidding document
    bidding_files = list(bidding_dir.glob("**/*.doc*"))

    if not bidding_files:
        print(f"❌ No bidding documents found in: {bidding_dir}")
        return False

    # Process first file
    test_file = bidding_files[0]
    print(f"📄 Processing: {test_file.name}")

    # Create output directory
    output_dir = project_root / "data" / "processed" / "bidding_test" / test_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Process the file
        result = pipeline.process_file(str(test_file), str(output_dir))

        # Print results
        print(f"\n📊 Processing Results:")
        print(f"Status: {result['status']}")

        if result["status"] == "completed":
            stats = result["statistics"]
            print(f"✅ Processing completed successfully")
            print(f"⏱️  Processing time: {stats['processing_time_seconds']:.2f} seconds")
            print(
                f"📝 Original content: {stats['original_content_length']:,} characters"
            )
            print(f"🧹 Cleaned content: {stats['cleaned_content_length']:,} characters")
            print(f"📦 Final chunks: {stats['final_chunks_count']}")
            print(
                f"📏 Average chunk size: {stats['average_chunk_size']:.0f} characters"
            )
            print(f"📈 Content coverage: {stats['content_coverage_ratio']:.1%}")

            # Print stage results
            print("\n🔍 Stage Results:")
            for stage_name, stage_data in result["stages"].items():
                if stage_data["success"]:
                    print(f"  ✅ {stage_name.title()}: Success")
                    if stage_name == "extraction":
                        print(
                            f"     - Content length: {stage_data['content_length']:,}"
                        )
                        if stage_data.get("bidding_type"):
                            print(f"     - Bidding type: {stage_data['bidding_type']}")
                    elif stage_name == "cleaning":
                        clean_stats = stage_data["stats"]
                        print(
                            f"     - Chars removed: {clean_stats['chars_removed']:,} ({clean_stats['reduction_percentage']:.1f}%)"
                        )
                    elif stage_name == "parsing":
                        print(f"     - Sections: {stage_data['sections_count']}")
                        print(f"     - Tables: {stage_data['tables_count']}")
                    elif stage_name == "chunking":
                        print(f"     - Chunks: {stage_data['chunks_count']}")
                        print(f"     - Avg size: {stage_data['avg_chunk_size']:.0f}")
                else:
                    print(f"  ❌ {stage_name.title()}: Failed")

            # Print validation results
            if "validation" in result and result["validation"]:
                validation = result["validation"]
                print(f"\n🔬 Data Integrity Validation:")
                print(f"  Valid: {validation['is_valid']}")
                print(f"  Coverage: {validation['coverage_percentage']:.1f}%")
                print(f"  Duplication: {validation['duplication_percentage']:.1f}%")

                if validation["issues"]:
                    print(f"  Issues ({len(validation['issues'])}):")
                    for issue in validation["issues"][:3]:
                        print(f"    - {issue}")
                    if len(validation["issues"]) > 3:
                        print(f"    ... and {len(validation['issues']) - 3} more")

            # Show first chunk example
            if result["final_chunks"]:
                first_chunk = result["final_chunks"][0]
                print(f"\n📝 First Chunk Example:")
                print(f"  Content length: {len(first_chunk.get('content', ''))}")
                print(f"  Content preview: {first_chunk.get('content', '')[:200]}...")

                metadata = first_chunk.get("metadata", {})
                if metadata:
                    print(f"  Metadata keys: {list(metadata.keys())}")
                    if metadata.get("hierarchy"):
                        print(f"  Hierarchy: {metadata['hierarchy']}")
                    if metadata.get("section_type"):
                        print(f"  Section type: {metadata['section_type']}")

            print(f"\n💾 Outputs saved to: {output_dir}")
            return True

        else:
            print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
            if result.get("errors"):
                for error in result["errors"]:
                    print(f"   - {error}")
            return False

    except Exception as e:
        print(f"❌ Exception during processing: {str(e)}")
        return False


def test_batch_processing():
    """Test batch processing of bidding documents"""

    print("\n=== Testing Batch Bidding Document Processing ===")

    # Initialize pipeline
    pipeline = BiddingPreprocessingPipeline(
        chunk_size=800,
        chunk_overlap=150,
        aggressive_cleaning=True,
        validate_integrity=True,
    )

    # Input and output directories
    input_dir = Path("/home/sakana/Code/RAG-bidding/data/raw/Ho so moi thau")
    output_dir = project_root / "data" / "processed" / "bidding_batch_test"

    if not input_dir.exists():
        print(f"❌ Input directory not found: {input_dir}")
        return False

    # Limit to first 2 files for testing
    all_files = list(input_dir.glob("**/*.doc*"))
    if len(all_files) > 2:
        print(f"📄 Found {len(all_files)} files, processing first 2 for testing")
        # Create temporary directory with subset
        test_input_dir = project_root / "temp_bidding_test"
        test_input_dir.mkdir(exist_ok=True)

        for i, file_path in enumerate(all_files[:2]):
            import shutil

            dest_path = test_input_dir / file_path.name
            shutil.copy2(file_path, dest_path)
            print(f"  {i+1}. {file_path.name}")

        input_dir = test_input_dir

    try:
        # Process batch
        print(f"\n🔄 Starting batch processing...")
        batch_result = pipeline.process_directory(
            str(input_dir), str(output_dir), file_pattern="*.doc*"
        )

        # Print batch results
        print(f"\n📊 Batch Processing Results:")
        print(f"Status: {batch_result['status']}")
        print(f"Files found: {batch_result['files_found']}")
        print(f"Files processed: {batch_result['files_processed']}")
        print(f"Files failed: {batch_result['files_failed']}")

        if batch_result.get("statistics"):
            stats = batch_result["statistics"]
            print(f"Total chunks: {stats['total_chunks']}")
            print(
                f"Average processing time: {stats['average_processing_time']:.2f} seconds"
            )
            print(
                f"Total content processed: {stats['total_content_processed']:,} characters"
            )

        # Show individual results
        success_count = 0
        for file_path, file_result in batch_result["results"].items():
            filename = os.path.basename(file_path)
            if file_result["status"] == "completed":
                chunks = len(file_result["final_chunks"])
                time_taken = file_result["statistics"]["processing_time_seconds"]
                print(f"  ✅ {filename}: {chunks} chunks in {time_taken:.1f}s")
                success_count += 1
            else:
                print(f"  ❌ {filename}: {file_result.get('error', 'Failed')}")

        print(
            f"\n🎯 Success Rate: {success_count}/{len(batch_result['results'])} ({success_count/len(batch_result['results'])*100:.0f}%)"
        )

        # Cleanup temporary directory
        if "temp_bidding_test" in str(input_dir):
            import shutil

            shutil.rmtree(input_dir)
            print("🧹 Cleaned up temporary test files")

        return success_count > 0

    except Exception as e:
        print(f"❌ Batch processing exception: {str(e)}")
        return False


def main():
    """Main test function"""

    print("🚀 Starting Bidding Document Preprocessing Pipeline Tests")
    print("=" * 60)

    setup_logging()

    # Test individual components
    success_count = 0
    total_tests = 2

    # Test 1: Single document processing
    if test_single_bidding_document():
        success_count += 1

    # Test 2: Batch processing
    if test_batch_processing():
        success_count += 1

    # Final results
    print("\n" + "=" * 60)
    print(f"🏁 Testing Complete: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print(
            "✅ All tests passed! Bidding preprocessing pipeline is working correctly."
        )
        return True
    else:
        print("❌ Some tests failed. Check logs for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
