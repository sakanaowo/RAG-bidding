#!/usr/bin/env python3
"""
Test Decree Preprocessing Pipeline

Test với file: ND 214 - 4.8.2025 - Thay thế NĐ24-original.docx
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.preprocessing.decree_preprocessing import DecreePreprocessingPipeline


def test_decree_pipeline():
    """Test decree pipeline với real file"""

    print("\n" + "=" * 80)
    print("TESTING DECREE PREPROCESSING PIPELINE")
    print("=" * 80)

    # Test file
    test_file = Path(
        "data/raw/Nghi dinh/ND 214 - 4.8.2025 - Thay thế NĐ24-original.docx"
    )

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return

    # Create pipeline
    pipeline = DecreePreprocessingPipeline(
        chunk_size=512,
        chunk_overlap=50,
        output_dir=Path("data/outputs/decree_test"),
        validate_integrity=True,  # Enable integrity checks
    )

    # Process file
    try:
        db_records = pipeline.process(test_file)

        print("\n" + "=" * 80)
        print("✅ PIPELINE TEST PASSED")
        print("=" * 80)
        print(f"Total chunks: {len(db_records)}")

        # Validate DB schema
        print("\n📊 DB Schema Validation:")
        if db_records:
            sample = db_records[0]
            required_fields = pipeline.metadata_mapper.REQUIRED_FIELDS

            print(f"  Required fields: {len(required_fields)}")
            print(f"  Sample fields: {len(sample.keys())}")

            missing = [f for f in required_fields if f not in sample]
            if missing:
                print(f"  ❌ Missing fields: {missing}")
            else:
                print(f"  ✅ All 25 fields present")

            # Show sample
            print("\n📝 Sample chunk:")
            print(f"  chunk_id: {sample['chunk_id']}")
            print(f"  doc_type: {sample['doc_type']}")
            print(f"  doc_number: {sample['doc_number']}")
            print(f"  doc_year: {sample['doc_year']}")
            print(f"  status: {sample['status']}")
            print(f"  hierarchy_path: {sample['hierarchy_path']}")
            print(f"  content: {sample['content'][:200]}...")

        # Statistics
        print("\n📈 Statistics:")
        total_chars = sum(len(r["content"]) for r in db_records)
        avg_chars = total_chars / len(db_records) if db_records else 0

        print(f"  Total chars: {total_chars:,}")
        print(f"  Avg chars per chunk: {avg_chars:.0f}")
        print(f"  Status distribution:")

        status_counts = {}
        for record in db_records:
            status = record["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            print(f"    {status}: {count}")

    except Exception as e:
        print(f"\n❌ PIPELINE TEST FAILED")
        print(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_decree_pipeline()
