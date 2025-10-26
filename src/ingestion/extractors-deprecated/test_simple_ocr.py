#!/usr/bin/env python3
"""
Simple OCR test script để test trước khi chạy batch lớn
"""
import os
import sys
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from vintern_batch_ocr import main


def main_test():
    # Test với 1 vài file đầu tiên
    script_dir = Path(__file__).parent.parent.parent.parent
    in_dir = str(
        script_dir
        / "app"
        / "data"
        / "processed"
        / "_image-process"
        / "Decreee-24-27-02-2024-images"
    )
    out_dir = str(
        script_dir
        / "app"
        / "data"
        / "processed"
        / "Decreee-24-27-02-2024-processed-test"
    )

    print(f"Testing with:")
    print(f"Input: {in_dir}")
    print(f"Output: {out_dir}")

    # Tạo một version giới hạn để test
    import glob

    files = sorted(
        [
            p
            for p in glob.glob(os.path.join(in_dir, "**/*"), recursive=True)
            if p.lower().endswith(
                (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")
            )
        ]
    )

    print(f"Found {len(files)} files total")

    # Chỉ process 3 file đầu để test
    test_files = files[:3]
    print(f"Testing with first 3 files: {[os.path.basename(f) for f in test_files]}")

    # Tạo một temp folder chỉ chứa 3 files này
    test_input_dir = str(script_dir / "temp_test_input")
    os.makedirs(test_input_dir, exist_ok=True)

    # Copy files to test directory
    import shutil

    for i, file_path in enumerate(test_files):
        dest = os.path.join(
            test_input_dir, f"test_{i+1:03d}_{os.path.basename(file_path)}"
        )
        shutil.copy2(file_path, dest)

    # Chạy main với test directory
    main(test_input_dir, out_dir)

    # Clean up
    shutil.rmtree(test_input_dir)
    print("Test completed!")


if __name__ == "__main__":
    main_test()
