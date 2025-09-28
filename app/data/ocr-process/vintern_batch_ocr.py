import os, glob, torch
from datetime import datetime
from PIL import Image
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer
from tqdm import tqdm
import json
import re
from typing import Dict, List, Tuple

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

# OCR quality validation thresholds
MIN_TEXT_LENGTH = 10  # Minimum characters for valid content
MIN_VIETNAMESE_WORDS = 3  # Minimum Vietnamese words
ERROR_PATTERNS = [
    r"\[OCR_ERROR:.*?\]",  # Our custom error markers
    r"^\s*$",  # Empty or whitespace only
    r"^\d+\s*$",  # Only page numbers
    r"^[^\w\sàáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]+$",  # No actual text content
]


class OCRLogger:
    """Logger class để theo dõi và ghi lại các lỗi OCR"""

    def __init__(self, log_file_path: str):
        self.log_file = log_file_path
        self.errors = []
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "errors": 0,
            "empty_content": 0,
            "low_quality": 0,
            "runtime_errors": 0,
        }

    def log_error(
        self,
        page_num: int,
        image_path: str,
        error_type: str,
        error_message: str = "",
        ocr_output: str = "",
    ):
        """Ghi lại lỗi OCR"""
        error_entry = {
            "page_number": page_num,
            "image_path": image_path,
            "error_type": error_type,
            "error_message": error_message,
            "ocr_output": ocr_output,
            "timestamp": datetime.now().isoformat(),
            "file_size_mb": self._get_file_size(image_path),
        }
        self.errors.append(error_entry)
        self.stats["errors"] += 1

        # Update specific error counters
        if error_type == "empty_content":
            self.stats["empty_content"] += 1
        elif error_type == "low_quality":
            self.stats["low_quality"] += 1
        elif error_type == "runtime_error":
            self.stats["runtime_errors"] += 1

    def log_success(self):
        """Ghi lại thành công"""
        self.stats["successful"] += 1

    def update_total(self):
        """Cập nhật tổng số trang đã xử lý"""
        self.stats["total_processed"] += 1

    def _get_file_size(self, file_path: str) -> float:
        """Lấy kích thước file (MB)"""
        try:
            return round(os.path.getsize(file_path) / (1024 * 1024), 2)
        except:
            return 0.0

    def save_log(self):
        """Lưu log ra file JSON"""
        log_data = {
            "summary": self.stats,
            "processing_date": datetime.now().isoformat(),
            "errors": self.errors,
        }

        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        print(f"\n📊 OCR Processing Summary:")
        print(f"   Total processed: {self.stats['total_processed']}")
        print(f"   Successful: {self.stats['successful']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"     - Empty content: {self.stats['empty_content']}")
        print(f"     - Low quality: {self.stats['low_quality']}")
        print(f"     - Runtime errors: {self.stats['runtime_errors']}")
        print(f"   Log saved to: {self.log_file}")


def validate_ocr_output(text: str) -> Tuple[bool, str]:
    """
    Kiểm tra chất lượng output OCR
    Returns: (is_valid, error_reason)
    """
    if not text or not text.strip():
        return False, "empty_output"

    # Check for error patterns
    for pattern in ERROR_PATTERNS:
        if re.match(pattern, text.strip()):
            return False, "error_pattern_match"

    # Check minimum length
    if len(text.strip()) < MIN_TEXT_LENGTH:
        return False, "too_short"

    # Check for actual Vietnamese content (not just page numbers)
    vietnamese_chars = re.findall(r"[\u00e0-\u1ef9]", text)  # Vietnamese characters
    words = re.findall(r"[a-zA-Z\u00e0-\u1ef9]+", text)  # Words with Vietnamese chars

    if len(vietnamese_chars) < 5:  # Too few Vietnamese characters
        return False, "insufficient_vietnamese_content"

    if len(words) < MIN_VIETNAMESE_WORDS:
        return False, "too_few_words"

    # Check if it's mostly numbers (page numbers, etc.)
    numbers = re.findall(r"\d+", text)
    if len("".join(numbers)) > len(text.strip()) * 0.8:
        return False, "mostly_numbers"

    return True, "valid"


def build_transform(sz):
    return T.Compose(
        [
            T.Lambda(lambda img: img.convert("RGB") if img.mode != "RGB" else img),
            T.Resize((sz, sz), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


# Tiling 448x448 như model card
def dynamic_preprocess(
    image, min_num=1, max_num=12, image_size=448, use_thumbnail=True
):
    w, h = image.size
    aspect = w / h
    target = sorted(
        {
            (i, j)
            for n in range(min_num, max_num + 1)
            for i in range(1, n + 1)
            for j in range(1, n + 1)
            if i * j <= max_num and i * j >= min_num
        },
        key=lambda x: x[0] * x[1],
    )
    # chọn lưới gần tỉ lệ ảnh nhất
    best = min(target, key=lambda r: abs(aspect - (r[0] / r[1])))
    tw, th = image_size * best[0], image_size * best[1]
    blocks = best[0] * best[1]
    img = image.resize((tw, th))
    out = []
    for i in range(blocks):
        box = (
            (i % (tw // image_size)) * image_size,
            (i // (tw // image_size)) * image_size,
            ((i % (tw // image_size)) + 1) * image_size,
            ((i // (tw // image_size)) + 1) * image_size,
        )
        out.append(img.crop(box))
    if use_thumbnail and len(out) != 1:
        out.append(image.resize((image_size, image_size)))
    return out


def load_tensor(
    path,
    input_size=448,
    max_num=12,
    device="cuda",  # Restored max_num to 12 for better coverage
):
    image = Image.open(path).convert("RGB")
    patches = dynamic_preprocess(
        image, image_size=input_size, max_num=max_num, use_thumbnail=True
    )
    tfm = build_transform(input_size)
    px = torch.stack([tfm(p) for p in patches])
    dtype = torch.bfloat16 if device == "cuda" else torch.float32
    return px.to(dtype).to(device)


def ocr_vintern(
    model,
    tok,
    pixel_values,
    logger: OCRLogger = None,
    page_num: int = 0,
    image_path: str = "",
):
    prompt = (
        "<image>\nHãy trích xuất TOÀN BỘ văn bản trong ảnh theo đúng thứ tự đọc. "
        "Chỉ trả về **văn bản thuần** (plain text), giữ nguyên xuống dòng, "
        "không thêm lời giải thích hay ký hiệu lạ."
    )
    cfg = dict(
        max_new_tokens=2048,  # Keep high for complete content extraction
        do_sample=False,
        num_beams=3,  # Increased from 1 to 3 for better quality (match notebook)
        repetition_penalty=3.5,  # Increased from 1.2 to 3.5 to avoid repetition (match notebook)
    )
    try:
        # Add timeout and better error handling
        with torch.no_grad():  # Ensure no gradients are computed
            text, _ = model.chat(
                tok,
                pixel_values,
                prompt,
                generation_config=cfg,
                history=None,
                return_history=True,
            )

        # Validate OCR output quality
        is_valid, validation_error = validate_ocr_output(text.strip())

        if not is_valid:
            error_msg = f"OCR validation failed: {validation_error}"
            if logger:
                if validation_error in ["empty_output", "too_short", "too_few_words"]:
                    logger.log_error(
                        page_num, image_path, "empty_content", error_msg, text.strip()
                    )
                else:
                    logger.log_error(
                        page_num, image_path, "low_quality", error_msg, text.strip()
                    )
            return f"[OCR_WARNING: {validation_error}] {text.strip()}"

        return text.strip()

    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            error_msg = f"GPU out of memory error: {e}"
            print(f"GPU out of memory error: {e}")
            if logger:
                logger.log_error(page_num, image_path, "runtime_error", error_msg)
            return "[OCR_ERROR: GPU out of memory - image too complex]"
        else:
            error_msg = f"Runtime error during OCR processing: {e}"
            print(f"Runtime error during OCR processing: {e}")
            if logger:
                logger.log_error(page_num, image_path, "runtime_error", error_msg)
            return "[OCR_ERROR: Runtime error during processing]"
    except Exception as e:
        error_msg = f"Error during OCR processing: {e}"
        print(f"Error during OCR processing: {e}")
        if logger:
            logger.log_error(page_num, image_path, "runtime_error", error_msg)
        return "[OCR_ERROR: Could not extract text from image]"


def main(in_dir, out_dir):
    # Validate input directory exists
    if not os.path.exists(in_dir):
        print(f"Error: Input directory '{in_dir}' does not exist")
        return

    try:
        os.makedirs(out_dir, exist_ok=True)
    except PermissionError as e:
        print(f"Error: Cannot create output directory '{out_dir}': {e}")
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    # Initialize logger
    log_file = os.path.join(out_dir, "ocr_processing_log.json")
    logger = OCRLogger(log_file)

    try:
        model = (
            AutoModel.from_pretrained(
                "5CD-AI/Vintern-1B-v3_5",
                dtype=(torch.bfloat16 if device == "cuda" else torch.float32),
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                use_flash_attn=False,
            )
            .eval()
            .to(device)
        )
        tok = AutoTokenizer.from_pretrained(
            "5CD-AI/Vintern-1B-v3_5", trust_remote_code=True, use_fast=False
        )
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    exts = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")
    files = sorted(
        [
            p
            for p in glob.glob(os.path.join(in_dir, "**/*"), recursive=True)
            if p.lower().endswith(exts)
        ]
    )

    if not files:
        print(f"No image files found in '{in_dir}'")
        return

    print(f"Found {len(files)} image files to process")

    # Create merged OCR markdown file - consistent naming like Law-2023-processed
    merged_md = os.path.join(out_dir, "final.md")

    try:
        with open(merged_md, "w", encoding="utf-8") as merged:
            for i, path in enumerate(
                tqdm(files, desc="Processing images", unit="img"), 1
            ):
                logger.update_total()

                try:
                    px = load_tensor(
                        path,
                        input_size=448,
                        max_num=12,
                        device=device,  # Restored to 12 patches
                    )
                    text = ocr_vintern(model, tok, px, logger, i, path)

                    # Generate consistent page naming: page_001.txt, page_002.txt, etc.
                    page_num = f"page_{i:03d}"
                    out_txt = os.path.join(out_dir, f"{page_num}.txt")

                    with open(out_txt, "w", encoding="utf-8") as f:
                        f.write(text)

                    # Add to merged file with metadata
                    merged.write(
                        f"---\n# {page_num}\nsource: {path}\ndatetime: {datetime.now().isoformat()}\nmodel: Vintern-1B-v3.5\n---\n\n{text}\n\n"
                    )

                    # Check if this was a successful extraction (no error markers)
                    if not any(
                        error_marker in text
                        for error_marker in ["[OCR_ERROR:", "[OCR_WARNING:"]
                    ):
                        logger.log_success()
                        tqdm.write(
                            f"✓ [{i}/{len(files)}] {os.path.basename(path)} -> {page_num}.txt"
                        )
                    else:
                        tqdm.write(
                            f"⚠ [{i}/{len(files)}] {os.path.basename(path)} -> {page_num}.txt (with issues)"
                        )

                    # Clear GPU cache if using CUDA
                    if device == "cuda":
                        torch.cuda.empty_cache()

                except Exception as e:
                    logger.log_error(
                        i, path, "runtime_error", f"Processing exception: {e}"
                    )
                    tqdm.write(
                        f"✗ [{i}/{len(files)}] ERROR processing {os.path.basename(path)}: {e}"
                    )
                    continue

    except Exception as e:
        print(f"Error writing output files: {e}")
        return

    # Save processing log
    logger.save_log()

    print("Done:", merged_md)
    if logger.stats["errors"] > 0:
        print(
            f"⚠ {logger.stats['errors']} pages had issues. Check the log file: {log_file}"
        )

    # Show detailed error summary if there are issues
    if logger.errors:
        print(f"\n🔍 Issues found:")
        error_types = {}
        for error in logger.errors:
            error_type = error["error_type"]
            if error_type not in error_types:
                error_types[error_type] = []
            error_types[error_type].append(f"page_{error['page_number']:03d}")

        for error_type, pages in error_types.items():
            print(f"   {error_type}: {', '.join(pages[:5])}")
            if len(pages) > 5:
                print(f"      ... and {len(pages) - 5} more")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Get script directory to make paths relative to project root
    # Script is at: RAG-bidding/app/data/ocr-process/vintern_batch_ocr.py
    # So parent.parent.parent goes to RAG-bidding/
    script_dir = Path(__file__).parent.parent.parent.parent

    if len(sys.argv) > 1:
        # User provided specific input directory
        in_dir = sys.argv[1]
        in_path = Path(in_dir)

        # Determine appropriate output directory
        if len(sys.argv) > 2:
            out_dir = sys.argv[2]
        else:
            # Auto-generate output directory based on input
            # Examples:
            # app/data/processed/image-process/Decreee-24-27-02-2024-images -> app/data/processed/Decreee-24-27-02-2024-processed
            # app/data/processed/image-process/Law-2023-images -> app/data/processed/Law-2023-processed

            if "_image_process" in str(in_path):
                # Extract the final folder name and create corresponding processed folder
                folder_name = in_path.name  # e.g., "Decreee-24-27-02-2024-images"
                # Remove "-images" suffix if present and add "-processed"
                if folder_name.endswith("-images"):
                    base_name = folder_name[:-7]  # Remove "-images"
                else:
                    base_name = folder_name
                out_dir = str(
                    script_dir
                    / "app"
                    / "data"
                    / "processed"
                    / "_file_process"
                    / f"{base_name}-processed"
                )
            else:
                # Default fallback
                out_dir = str(
                    script_dir
                    / "app"
                    / "data"
                    / "processed"
                    / "_file_process"
                    / f"{in_path.name}-processed"
                )
    else:
        # Default: process all folders in image-process directory
        print("No input directory specified.")
        print("Usage: python vintern_batch_ocr.py <input_directory> [output_directory]")
        print("Examples:")
        print(
            "  python vintern_batch_ocr.py app/data/processed/_image_process/Decreee-24-27-02-2024-images"
        )
        print(
            "  python vintern_batch_ocr.py app/data/processed/_image_process/Law-2023-images"
        )
        sys.exit(1)

    print(f"Input directory: {in_dir}")
    print(f"Output directory: {out_dir}")

    main(in_dir, out_dir)
