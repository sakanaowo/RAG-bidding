#!/usr/bin/env python3
"""
Debug metadata extraction from DOCX files
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from preprocessing.loaders.docx_loader import DocxLoader


def debug_metadata(file_path: Path):
    """Debug metadata extraction"""
    print(f"\n{'='*60}")
    print(f"Debug metadata for: {file_path}")
    print(f"{'='*60}")

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    try:
        loader = DocxLoader()
        raw_content = loader.load(file_path)

        print("📋 Full metadata:")
        for key, value in raw_content.metadata.items():
            print(f"   {key}: {repr(value)}")

        print(f"\n📄 Text preview (first 200 chars):")
        print(f"   {raw_content.text[:200]}...")

    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main debug function"""
    print("🔍 Debug Metadata Extraction")

    # Test files to debug
    test_files = [
        "data/raw/Luat chinh/Luat so 57 2024 QH15.docx",
        "data/raw/Luat chinh/Luat so 90 2025-qh15.docx",
    ]

    for file_path_str in test_files:
        file_path = Path(file_path_str)
        debug_metadata(file_path)


if __name__ == "__main__":
    main()
