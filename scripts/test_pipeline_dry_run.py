#!/usr/bin/env python3
"""
Test Pipeline Dry Run
Kiểm tra pipeline với files thực tế trong data/raw
"""

import sys
from pathlib import Path
import traceback

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from preprocessing.pipelines.law_pipeline import LawPipeline
from preprocessing.loaders.docx_loader import DocxLoader
from preprocessing.loaders.pdf_loader import PdfLoader


def test_single_file(file_path: Path, pipeline_class=None):
    """Test a single file with appropriate pipeline"""
    print(f"\n{'='*60}")
    print(f"Testing: {file_path}")
    print(f"{'='*60}")

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return False

    try:
        # Determine appropriate loader
        ext = file_path.suffix.lower()
        if ext == ".docx":
            loader = DocxLoader()
            if pipeline_class is None:
                pipeline_class = LawPipeline  # Default for law files
        elif ext == ".pdf":
            loader = PdfLoader()
            print("⚠️  PDF files not supported by LawPipeline yet")
            return True  # Skip PDF for now
        else:
            print(f"⚠️  Unsupported file extension: {ext}")
            return True

        print(f"📁 Loading file with {loader.__class__.__name__}...")
        raw_content = loader.load(file_path)
        print(f"✅ Loaded successfully")
        print(f"   - Text length: {len(raw_content.text)}")
        print(f"   - Metadata keys: {list(raw_content.metadata.keys())}")

        if pipeline_class:
            print(f"🔄 Testing {pipeline_class.__name__}...")
            pipeline = pipeline_class()
            result = pipeline.process(file_path)

            if result.success:
                print(f"✅ Pipeline succeeded!")
                print(f"   - Chunks created: {len(result.chunks)}")
                print(
                    f"   - Processing time: {result.metadata.get('duration_ms', 'N/A')}ms"
                )

                # Show first chunk sample
                if result.chunks:
                    first_chunk = result.chunks[0]
                    print(
                        f"   - First chunk preview: {first_chunk.content_structure.content_text[:100]}..."
                    )

                return True
            else:
                print(f"❌ Pipeline failed!")
                for error in result.errors:
                    print(f"   - Error: {error}")
                return False
        else:
            print("⚠️  No pipeline specified, only tested loader")
            return True

    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("🚀 Starting Pipeline Dry Run Test")
    print("Testing files in data/raw with existing pipelines")

    # Test files to check
    test_files = [
        "data/raw/Luat chinh/Luat so 57 2024 QH15.docx",
        "data/raw/Luat chinh/Luat so 90 2025-qh15.docx",
        "data/raw/Luat chinh/Luat dau thau 2023.docx",
        "data/raw/Luat chinh/HỢP NHẤT 126 2025 về Luật đấu thầu.docx",
    ]

    results = []

    for file_path_str in test_files:
        file_path = Path(file_path_str)
        success = test_single_file(file_path, LawPipeline)
        results.append((file_path_str, success))

    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    successful = sum(1 for _, success in results if success)
    total = len(results)

    print(f"Total files tested: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")

    for file_path, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {file_path}")

    if successful == total:
        print("\n🎉 All tests passed! Pipeline works with existing files.")
        print("   -> Issue is likely in upload service integration")
    else:
        print(f"\n⚠️  {total - successful} files failed")
        print("   -> Pipeline may need updates for some file formats")


if __name__ == "__main__":
    main()
