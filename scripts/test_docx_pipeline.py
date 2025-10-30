"""
Test DOCX Processing Pipeline

Usage:
    python scripts/test_docx_pipeline.py
"""

import sys
from pathlib import Path

# Add project root to path (must be before imports)
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
print(f"✓ Added to sys.path: {project_root}")
print(f"✓ Current sys.path: {sys.path[:3]}")

from src.preprocessing.law_preprocessing import LawPreprocessingPipeline


def main():
    print("=" * 80)
    print("DOCX PROCESSING PIPELINE - TEST")
    print("=" * 80)

    # Test files
    test_files = [
        "data/raw/Luat chinh/Luat so 90 2025-qh15.docx",
        "data/raw/Nghi dinh/ND 214 - 4.8.2025 - Thay thế NĐ24-original.docx",
    ]
    output_dir = Path("data/processed/test_output")

    # Initialize pipeline
    print("\n🔧 Initializing pipeline...")
    pipeline = LawPreprocessingPipeline(
        max_chunk_size=2000, min_chunk_size=300, aggressive_clean=False
    )

    # Process each file
    for docx_file_path in test_files:
        docx_file = Path(docx_file_path)

        if not docx_file.exists():
            print(f"\n❌ File not found: {docx_file}")
            continue

        print("\n" + "=" * 80)
        print(f"PROCESSING: {docx_file.name}")
        print("=" * 80)

        # Process file
        try:
            results = pipeline.process_single_file(docx_file, output_dir)

            # Display summary
            print("\n📊 Statistics:")
            print(
                f"   Extracted chars: {results['statistics']['extraction']['char_count']:,}"
            )
            print(
                f"   Điều count: {results['statistics']['structure'].get('dieu_count', 0)}"
            )
            print(f"   Chunks created: {len(results['chunks'])}")
            print(
                f"   Avg chunk size: {results['statistics']['chunking']['avg_chunk_size']:.0f} chars"
            )
            print(f"   💾 Outputs: {output_dir}/{docx_file.stem}_*")

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ All tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
