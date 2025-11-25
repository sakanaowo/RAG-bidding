#!/usr/bin/env python3
"""
Test script for bidding document preprocessing pipeline with HSYC templates

Tests the complete bidding document preprocessing pipeline with HSYC template documents.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.preprocessing.bidding_preprocessing import BiddingPreprocessingPipeline


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("hsyc_preprocessing_test.log"),
        ],
    )


def test_hsyc_templates():
    """Test processing HSYC template documents"""

    print("🚀 Testing HSYC Template Documents Processing")
    print("=" * 60)

    # Initialize pipeline with settings optimized for templates
    pipeline = BiddingPreprocessingPipeline(
        chunk_size=800,  # Smaller chunks for template analysis
        chunk_overlap=150,  # Moderate overlap
        aggressive_cleaning=False,  # Keep template formatting
        validate_integrity=True,
    )

    # Print pipeline info
    pipeline_info = pipeline.get_pipeline_info()
    print(f"Pipeline: {pipeline_info['pipeline_type']}")
    print(f"Components: {list(pipeline_info['components'].values())}")
    print(f"Configuration: chunk_size={pipeline_info['configuration']['chunk_size']}")

    # HSYC templates directory
    hsyc_dir = Path("/home/sakana/Code/RAG-bidding/data/raw/Ho so moi thau/1. Mẫu HSYC")

    if not hsyc_dir.exists():
        print(f"❌ HSYC templates directory not found: {hsyc_dir}")
        return False

    # Find all HSYC template files
    hsyc_files = list(hsyc_dir.glob("*.docx"))

    if not hsyc_files:
        print(f"❌ No HSYC template files found in: {hsyc_dir}")
        return False

    print(f"\n📄 Found {len(hsyc_files)} HSYC template files:")
    for i, file_path in enumerate(hsyc_files, 1):
        print(f"  {i}. {file_path.name}")

    # Create output directory
    output_dir = project_root / "data" / "processed" / "hsyc_templates_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each HSYC template
    success_count = 0
    results = {}

    for file_path in hsyc_files:
        print(f"\n{'='*50}")
        print(f"📄 Processing: {file_path.name}")
        print(f"{'='*50}")

        try:
            # Create specific output directory for this template
            template_output_dir = output_dir / file_path.stem
            template_output_dir.mkdir(exist_ok=True)

            # Process the template
            result = pipeline.process_file(str(file_path), str(template_output_dir))

            results[file_path.name] = result

            # Print results
            if result["status"] == "completed":
                stats = result["statistics"]
                print(f"✅ Processing completed successfully")
                print(
                    f"⏱️  Processing time: {stats['processing_time_seconds']:.2f} seconds"
                )
                print(
                    f"📝 Original content: {stats['original_content_length']:,} characters"
                )
                print(
                    f"🧹 Cleaned content: {stats['cleaned_content_length']:,} characters"
                )
                print(f"📦 Final chunks: {stats['final_chunks_count']}")
                print(
                    f"📏 Average chunk size: {stats['average_chunk_size']:.0f} characters"
                )
                print(f"📈 Content coverage: {stats['content_coverage_ratio']:.1%}")

                # Show template type detection
                extraction_stage = result["stages"].get("extraction", {})
                if extraction_stage.get("metadata", {}).get("document_category"):
                    print(
                        f"🏷️  Template type: {extraction_stage['metadata']['document_category']}"
                    )

                # Show bidding type if detected
                if extraction_stage.get("metadata", {}).get("bidding_type"):
                    print(
                        f"🔧 Bidding type: {extraction_stage['metadata']['bidding_type']}"
                    )

                # Print stage results
                print(f"\n🔍 Stage Results:")
                for stage_name, stage_data in result["stages"].items():
                    if stage_data["success"]:
                        print(f"  ✅ {stage_name.title()}: Success")
                        if stage_name == "extraction":
                            print(
                                f"     - Content length: {stage_data['content_length']:,}"
                            )
                            print(f"     - Tables: {stage_data.get('tables_count', 0)}")
                        elif stage_name == "cleaning":
                            clean_stats = stage_data["stats"]
                            reduction = clean_stats["reduction_percentage"]
                            if reduction > 0:
                                print(f"     - Content reduced: {reduction:.1f}%")
                            else:
                                print(f"     - Content expanded: {abs(reduction):.1f}%")
                        elif stage_name == "parsing":
                            print(f"     - Sections: {stage_data['sections_count']}")
                            print(f"     - Tables: {stage_data['tables_count']}")
                        elif stage_name == "chunking":
                            print(f"     - Chunks: {stage_data['chunks_count']}")
                            print(
                                f"     - Avg size: {stage_data['avg_chunk_size']:.0f}"
                            )
                    else:
                        print(f"  ❌ {stage_name.title()}: Failed")

                # Print validation results
                if "validation" in result and result["validation"]:
                    validation = result["validation"]
                    print(f"\n🔬 Data Integrity Validation:")
                    print(f"  Valid: {validation['is_valid']}")
                    print(f"  Coverage: {validation['coverage_percentage']:.1f}%")
                    print(
                        f"  Checks: {validation['passed_checks']}/{validation['total_checks']} passed"
                    )

                    if validation.get("issues") and len(validation["issues"]) > 0:
                        print(f"  Issues ({len(validation['issues'])}):")
                        for issue in validation["issues"][:2]:
                            print(f"    - {issue}")
                        if len(validation["issues"]) > 2:
                            print(f"    ... and {len(validation['issues']) - 2} more")

                # Show first chunk example for template analysis
                if result["final_chunks"]:
                    first_chunk = result["final_chunks"][0]
                    print(f"\n📝 Template Content Preview:")
                    print(f"  Content length: {len(first_chunk.get('content', ''))}")

                    content_preview = first_chunk.get("content", "")[:300]
                    print(f"  Content: {repr(content_preview)}...")

                    metadata = first_chunk.get("metadata", {})
                    if metadata:
                        print(f"  Metadata keys: {list(metadata.keys())}")
                        if metadata.get("section_type"):
                            print(f"  Section type: {metadata['section_type']}")
                        if metadata.get("contains_forms"):
                            print(f"  Contains forms: {metadata['contains_forms']}")
                        if metadata.get("contains_technical_specs"):
                            print(
                                f"  Contains tech specs: {metadata['contains_technical_specs']}"
                            )

                print(f"\n💾 Template outputs saved to: {template_output_dir}")
                success_count += 1

            else:
                print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                if result.get("errors"):
                    for error in result["errors"]:
                        print(f"   - {error}")

        except Exception as e:
            print(f"❌ Exception during processing: {str(e)}")
            results[file_path.name] = {"status": "failed", "error": str(e)}

    # Summary
    print(f"\n{'='*60}")
    print(f"🎯 HSYC Templates Processing Summary")
    print(f"{'='*60}")
    print(f"Total templates: {len(hsyc_files)}")
    print(f"Successfully processed: {success_count}")
    print(f"Failed: {len(hsyc_files) - success_count}")
    print(f"Success rate: {success_count/len(hsyc_files)*100:.0f}%")

    # Per-template summary
    print(f"\n📊 Per-Template Results:")
    for filename, result in results.items():
        if result["status"] == "completed":
            chunks = len(result["final_chunks"])
            time_taken = result["statistics"]["processing_time_seconds"]
            coverage = result["statistics"]["content_coverage_ratio"]
            print(
                f"  ✅ {filename}: {chunks} chunks, {time_taken:.2f}s, {coverage:.0%} coverage"
            )
        else:
            error_msg = result.get("error", "Failed")[:50]
            print(f"  ❌ {filename}: {error_msg}")

    # Template type analysis
    template_types = {}
    for filename, result in results.items():
        if result["status"] == "completed":
            extraction = result["stages"].get("extraction", {})
            doc_category = extraction.get("metadata", {}).get(
                "document_category", "unknown"
            )
            template_types[doc_category] = template_types.get(doc_category, 0) + 1

    if template_types:
        print(f"\n🏷️  Template Types Detected:")
        for template_type, count in template_types.items():
            print(f"  - {template_type}: {count} templates")

    return success_count == len(hsyc_files)


def main():
    """Main test function"""

    print("🏗️  Starting HSYC Template Documents Preprocessing Tests")

    setup_logging()

    # Test HSYC templates
    success = test_hsyc_templates()

    if success:
        print(
            "\n🎉 All HSYC template tests passed! Pipeline is working correctly with templates."
        )
        return True
    else:
        print("\n⚠️  Some HSYC template tests failed. Check logs for details.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
