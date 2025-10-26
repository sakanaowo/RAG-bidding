#!/usr/bin/env python3
"""
Script phân tích lại các file OCR đã xử lý để tìm các trang có vấn đề
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import our OCR module
sys.path.append(str(Path(__file__).parent))

from vintern_batch_ocr import OCRLogger, validate_ocr_output


def analyze_processed_folder(processed_dir: str):
    """Phân tích folder đã được xử lý OCR để tìm các trang có vấn đề"""
    processed_path = Path(processed_dir)

    if not processed_path.exists():
        print(f"❌ Folder không tồn tại: {processed_dir}")
        return

    # Tìm tất cả file .txt có pattern page_xxx.txt
    txt_files = sorted(processed_path.glob("page_*.txt"))

    if not txt_files:
        print(f"❌ Không tìm thấy file OCR trong folder: {processed_dir}")
        return

    print(f"🔍 Phân tích {len(txt_files)} trang OCR trong: {processed_dir}")
    print("-" * 70)

    # Initialize logger for analysis
    log_file = processed_path / "analysis_log.json"
    logger = OCRLogger(str(log_file))

    problematic_pages = []

    for txt_file in txt_files:
        try:
            # Extract page number from filename (page_001.txt -> 1)
            page_num = int(txt_file.stem.split("_")[1])

            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()

            logger.update_total()

            # Validate content
            is_valid, error_reason = validate_ocr_output(content)

            if is_valid:
                logger.log_success()
                print(f"✓ {txt_file.name}: OK ({len(content)} chars)")
            else:
                logger.log_error(
                    page_num,
                    str(txt_file),
                    error_reason,
                    f"Content validation failed: {error_reason}",
                    content[:200],
                )
                problematic_pages.append(
                    {
                        "file": txt_file.name,
                        "page_num": page_num,
                        "error": error_reason,
                        "content_length": len(content),
                        "content_preview": content[:100].replace("\n", "\\n"),
                    }
                )
                print(f"⚠ {txt_file.name}: {error_reason} ({len(content)} chars)")
                if len(content) < 100:
                    print(f"   Content: '{content.strip()}'")

        except Exception as e:
            print(f"❌ Lỗi khi đọc {txt_file.name}: {e}")
            logger.log_error(0, str(txt_file), "read_error", str(e))

    # Save analysis log
    logger.save_log()

    print(f"\n📊 Tóm tắt phân tích:")
    print(f"   📁 Folder: {processed_dir}")
    print(f"   📄 Tổng số trang: {len(txt_files)}")
    print(f"   ✅ Thành công: {logger.stats['successful']}")
    print(f"   ⚠  Có vấn đề: {logger.stats['errors']}")

    if problematic_pages:
        print(f"\n🚨 Chi tiết các trang có vấn đề:")
        for page in problematic_pages[:10]:  # Show first 10 problematic pages
            print(f"   {page['file']}: {page['error']} - {page['content_preview']}")

        if len(problematic_pages) > 10:
            print(f"   ... và {len(problematic_pages) - 10} trang khác")

    print(f"\n📋 Log chi tiết được lưu tại: {log_file}")

    # Create a summary report
    create_summary_report(processed_path, problematic_pages, logger.stats)


def create_summary_report(processed_path: Path, problematic_pages: list, stats: dict):
    """Tạo báo cáo tóm tắt dạng markdown"""
    report_file = processed_path / "ocr_analysis_report.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"# Báo cáo phân tích OCR\n\n")
        f.write(
            f"**Thời gian phân tích:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
        )
        f.write(f"**Folder:** `{processed_path.name}`\n\n")

        f.write(f"## Tóm tắt\n\n")
        f.write(f"- **Tổng số trang:** {stats['total_processed']}\n")
        f.write(
            f"- **Thành công:** {stats['successful']} ({stats['successful']/stats['total_processed']*100:.1f}%)\n"
        )
        f.write(
            f"- **Có vấn đề:** {stats['errors']} ({stats['errors']/stats['total_processed']*100:.1f}%)\n\n"
        )

        if stats["errors"] > 0:
            f.write(f"### Phân loại lỗi\n")
            f.write(f"- **Nội dung trống:** {stats['empty_content']}\n")
            f.write(f"- **Chất lượng thấp:** {stats['low_quality']}\n")
            f.write(f"- **Lỗi xử lý:** {stats['runtime_errors']}\n\n")

        if problematic_pages:
            f.write(f"## Chi tiết các trang có vấn đề\n\n")
            f.write(f"| Trang | Lỗi | Độ dài | Nội dung preview |\n")
            f.write(f"|-------|-----|--------|------------------|\n")
            for page in problematic_pages:
                f.write(
                    f"| {page['file']} | {page['error']} | {page['content_length']} | `{page['content_preview']}` |\n"
                )

        f.write(f"\n## Khuyến nghị\n\n")
        if stats["empty_content"] > 0:
            f.write(
                f"- **Nội dung trống:** {stats['empty_content']} trang cần xử lý lại OCR\n"
            )
        if stats["low_quality"] > 0:
            f.write(
                f"- **Chất lượng thấp:** {stats['low_quality']} trang có thể cần điều chỉnh preprocessing\n"
            )
        if stats["runtime_errors"] > 0:
            f.write(
                f"- **Lỗi xử lý:** {stats['runtime_errors']} trang cần kiểm tra ảnh đầu vào\n"
            )

    print(f"📄 Báo cáo markdown được lưu tại: {report_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_processed_ocr.py <processed_folder_path>")
        print("Example:")
        print(
            "  python3 analyze_processed_ocr.py app/data/processed/Decreee-24-27-02-2024-processed"
        )
        sys.exit(1)

    processed_folder = sys.argv[1]
    analyze_processed_folder(processed_folder)
