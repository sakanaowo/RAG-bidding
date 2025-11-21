"""
Simple Document Metadata Extractor
Extracts basic metadata from 70 files in 7 categories
"""

import json
from pathlib import Path
from typing import List, Dict
import hashlib
from datetime import datetime

# Category mapping: folder → (document_type, category_display_name)
CATEGORY_MAP = {
    "Luat chinh": ("law", "Luật chính"),
    "Nghi dinh": ("decree", "Nghị định"),
    "Thong tu": ("circular", "Thông tư"),
    "Quyet dinh": ("decision", "Quyết định"),
    "Ho so moi thau": ("bidding_form", "Hồ sơ mời thầu"),
    "Mau bao cao": ("report_template", "Mẫu báo cáo"),
    "Cau hoi thi": ("exam_question", "Câu hỏi thi"),
}

# Mapping for folder names with diacritics (actual folder names)
FOLDER_MAP = {
    "Luat chinh": "Luat chinh",
    "Nghi dinh": "Nghi dinh",
    "Thong tu": "Thong tu",
    "Quyet dinh": "Quyet dinh",
    "Ho so moi thau": "Ho so moi thau",
    "Mau bao cao": "Mau bao cao",
    "Cau hoi thi": "Cau hoi thi",
}


def generate_document_id(file_path: Path, doc_type: str) -> str:
    """
    Generate simple document_id from filename

    Examples:
        Luat so 90 2025-qh15.docx → LUA-90-2025-QH15
        ND 214 - 4.8.2025.docx → ND-214-2025-CP
        01A. Mẫu HSYC Xây lắp.docx → FORM-HSYC-01A
    """
    filename = file_path.stem  # Without extension

    if doc_type == "law":
        # Extract: "Luat so 90 2025-qh15" → "LUA-90-2025-QH15"
        parts = filename.lower().split()
        if "so" in parts:
            idx = parts.index("so")
            number = parts[idx + 1] if idx + 1 < len(parts) else "00"
            # Find year
            year = "2025"
            for part in parts:
                if "20" in part and len(part) >= 4:
                    year = part[:4]
                    break
            return f"LUA-{number}-{year}-QH15"
        else:
            # Fallback
            return f"LUA-{filename[:20].replace(' ', '-')}"

    elif doc_type == "decree":
        # "ND 214 - 4.8.2025" → "ND-214-2025-CP"
        parts = filename.split()
        number = "000"
        year = "2025"
        for part in parts:
            if part.isdigit():
                number = part
            if "20" in part:
                year = part[:4]
        return f"ND-{number}-{year}-CP"

    elif doc_type == "circular":
        # Simple naming
        clean_name = filename.replace(".", "").replace(" ", "-")[:30]
        return f"TT-{clean_name}"

    elif doc_type == "decision":
        # "Quyết định-1667-QĐ-BYT" → "QD-1667-BYT"
        parts = filename.split("-")
        number = "0000"
        for part in parts:
            if part.isdigit():
                number = part
                break
        return f"QD-{number}-BYT"

    elif doc_type == "bidding_form":
        # "01A. Mẫu HSYC Xây lắp" → "FORM-HSYC-01A"
        parts = filename.split(".")
        code = parts[0].strip() if parts else "00"
        if "xây lắp" in filename.lower():
            return f"FORM-HSYC-XAYLAP-{code}"
        elif "hàng hóa" in filename.lower() or "hang hoa" in filename.lower():
            return f"FORM-HSYC-HANGHOA-{code}"
        elif "tư vấn" in filename.lower() or "tu van" in filename.lower():
            return f"FORM-HSYC-TUVAN-{code}"
        else:
            clean = filename[:20].replace(" ", "-").replace(".", "")
            return f"FORM-{clean}"

    elif doc_type == "report_template":
        # Simple template naming
        parts = filename.split(".")
        code = parts[0].strip() if parts else "00"
        return f"TEMPLATE-BC-{code}"

    elif doc_type == "exam_question":
        # Exam questions
        clean = filename[:20].replace(" ", "-").replace(".", "")
        return f"EXAM-{clean}"

    else:
        # Fallback: use hash of filename
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:8]
        return f"DOC-{hash_suffix}"


def extract_document_name(file_path: Path, doc_type: str) -> str:
    """Extract display name from filename"""
    filename = file_path.stem

    # Clean up common patterns
    filename = filename.replace("_", " ")
    filename = filename.replace("-original", "")
    filename = filename.strip()

    return filename


def extract_documents_from_folder(base_path: Path = Path("data/raw")) -> List[Dict]:
    """
    Scan all 7 folders and extract metadata for 70 documents
    """
    documents = []

    for folder_key, (doc_type, category) in CATEGORY_MAP.items():
        # Use actual folder name (may have diacritics)
        actual_folder = FOLDER_MAP.get(folder_key, folder_key)
        folder_path = base_path / actual_folder

        if not folder_path.exists():
            print(f"⚠️  Folder not found: {folder_path}")
            continue

        # Get all files (docx, doc, pdf) - including subdirectories
        for file_path in folder_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in [
                ".docx",
                ".doc",
                ".pdf",
            ]:

                # Generate document_id
                doc_id = generate_document_id(file_path, doc_type)

                # Extract display name
                doc_name = extract_document_name(file_path, doc_type)

                # Get relative path from project root
                try:
                    source_file = str(file_path.relative_to(Path.cwd()))
                except ValueError:
                    # If relative path fails, use absolute path
                    source_file = str(file_path)

                documents.append(
                    {
                        "document_id": doc_id,
                        "document_name": doc_name,
                        "category": category,
                        "document_type": doc_type,
                        "source_file": source_file,
                        "file_name": file_path.name,
                        "total_chunks": 0,  # Will be updated after processing
                        "status": "active",
                    }
                )

    return documents


def main():
    """Extract metadata and save to JSON"""
    print("🔍 Scanning data/raw folders...")

    documents = extract_documents_from_folder()

    print(f"\n✅ Found {len(documents)} documents\n")

    # Group by category for display
    by_category = {}
    for doc in documents:
        cat = doc["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(doc)

    # Display summary
    for category, docs in sorted(by_category.items()):
        print(f"📁 {category}: {len(docs)} documents")
        for doc in docs[:2]:  # Show first 2
            print(f"   - {doc['document_id']}: {doc['document_name'][:50]}")
        if len(docs) > 2:
            print(f"   ... and {len(docs) - 2} more")
        print()

    # Save to JSON
    output_path = Path("data/processed/documents_metadata.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print(f"💾 Saved to: {output_path}")
    print(f"📊 Total documents: {len(documents)}")

    return documents


if __name__ == "__main__":
    main()
