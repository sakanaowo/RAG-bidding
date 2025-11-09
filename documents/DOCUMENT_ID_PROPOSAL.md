# Document ID System - Đề xuất Logic

## Phân tích hệ thống hiện tại

### Vấn đề:
- Document ID hiện tại: `bidding_untitled`, `circular_untitled`, `decree_untitled`
- Không có cấu trúc chuẩn, thiếu metadata quan trọng (năm, số hiệu, loại)
- Khó tra cứu, khó quản lý khi scale lên

### Yêu cầu:
1. **Tính duy nhất (Uniqueness)**: Mỗi văn bản có ID riêng biệt
2. **Tính mô tả (Descriptive)**: Nhìn ID biết ngay loại văn bản, số hiệu, năm
3. **Tính mở rộng (Scalable)**: Dễ thêm văn bản mới, không conflict
4. **Tính tương thích ngược (Backward Compatible)**: Migration được data cũ
5. **Tính chuẩn hóa (Standardized)**: Theo quy ước pháp lý Việt Nam

---

## 🎯 OPTION 1: Legal Document Standard ID (Theo quy chuẩn pháp lý VN)

### Cấu trúc:
```
{số_hiệu}/{năm}/{loại_văn_bản}
```

### Ví dụ:
- Nghị định: `43/2022/NĐ-CP`, `50/2024/NĐ-CP`
- Thông tư: `20/2020/TT-BTC`, `15/2023/TT-BKHĐT`
- Quyết định: `123/2021/QĐ-TTg`, `456/2024/QĐ-BXD`
- Luật: `Law-59/2020/QH14` (Luật Xây dựng)
- Mẫu hồ sơ: `Form-17/2022/Bidding`, `Template-05/2023/Report`

### Migration logic:
```python
def migrate_to_legal_standard(old_id: str, metadata: dict) -> str:
    """
    Chuyển đổi ID cũ sang chuẩn pháp lý
    
    Ví dụ:
    - "circular_untitled" → "Circular-Unknown/2024/TT"
    - "decree_untitled" → "Decree-Unknown/2024/NĐ-CP"
    - "bidding_untitled" → "Form-Bidding/2024/Template"
    """
    doc_type = metadata.get("document_type", "unknown")
    year = metadata.get("year") or "2024"
    number = metadata.get("number") or "Unknown"
    
    type_map = {
        "law": f"Law-{number}/{year}/QH",
        "decree": f"{number}/{year}/NĐ-CP",
        "circular": f"{number}/{year}/TT",
        "decision": f"{number}/{year}/QĐ",
        "bidding": f"Form-Bidding/{year}/Template",
        "report": f"Form-Report/{year}/Template",
        "exam": f"Exam-{number}/{year}/Test"
    }
    
    return type_map.get(doc_type, f"{doc_type.title()}-{number}/{year}/DOC")
```

### Ưu điểm:
✅ Tuân thủ chuẩn pháp lý Việt Nam  
✅ Dễ nhận biết loại văn bản ngay từ ID  
✅ Tương thích với cách người dùng trích dẫn văn bản  
✅ Tự nhiên, không cần học thêm convention  

### Nhược điểm:
❌ Với văn bản không có số hiệu → cần xử lý đặc biệt  
❌ Một số văn bản có số hiệu dài, phức tạp  

### Use cases phù hợp:
- ✅ Hệ thống pháp lý chính thức
- ✅ Tra cứu văn bản theo số hiệu
- ✅ Integration với hệ thống khác (LuatVietnam.vn, ThiViLuat, etc.)

---

## 🎯 OPTION 2: UUID-based System (Chuẩn quốc tế)

### Cấu trúc:
```
{prefix}_{uuid_v4}
hoặc
{type}_{year}_{uuid_short}
```

### Ví dụ:
- `doc_550e8400-e29b-41d4-a716-446655440000`
- `decree_2024_a7f3c9e2`
- `circular_2023_b4d8e1f5`
- `form_2024_c9a2d7f3`

### Migration logic:
```python
import uuid
import hashlib

def migrate_to_uuid_system(old_id: str, metadata: dict) -> str:
    """
    Tạo UUID từ old_id để đảm bảo idempotent
    
    Ví dụ:
    - "circular_untitled" → "circular_2024_8f3a9c7e"
    - "decree_untitled" → "decree_2024_b2d5e8a1"
    """
    doc_type = metadata.get("document_type", "doc")
    year = metadata.get("year") or "2024"
    
    # Tạo UUID deterministic từ old_id (cùng input → cùng output)
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    doc_uuid = uuid.uuid5(namespace, old_id)
    uuid_short = str(doc_uuid)[:8]
    
    return f"{doc_type}_{year}_{uuid_short}"
```

### Ưu điểm:
✅ Đảm bảo uniqueness tuyệt đối  
✅ Không conflict khi scale lớn  
✅ Chuẩn quốc tế, dễ integrate với external systems  
✅ Không phụ thuộc vào metadata văn bản  

### Nhược điểm:
❌ Không human-readable  
❌ Khó tra cứu thủ công  
❌ Không mang thông tin về nội dung văn bản  

### Use cases phù hợp:
- ✅ Hệ thống internal với nhiều loại document
- ✅ Cần uniqueness tuyệt đối
- ✅ Tra cứu qua UI/API (không tra cứu trực tiếp bằng ID)

---

## 🎯 OPTION 3: Hierarchical System (Phân cấp theo taxonomy)

### Cấu trúc:
```
{category}/{subcategory}/{type}:{number}-{year}
```

### Ví dụ:
- `legal/legislative/law:59-2020` (Luật)
- `legal/executive/decree:43-2022` (Nghị định)
- `legal/ministerial/circular:20-2020` (Thông tư)
- `bidding/forms/template:17-2022` (Mẫu hồ sơ)
- `bidding/questions/exam:01-2024` (Câu hỏi thi)

### Migration logic:
```python
def migrate_to_hierarchical_system(old_id: str, metadata: dict) -> str:
    """
    Tạo ID phân cấp theo taxonomy
    
    Ví dụ:
    - "law_untitled" → "legal/legislative/law:unknown-2024"
    - "decree_untitled" → "legal/executive/decree:unknown-2024"
    - "circular_untitled" → "legal/ministerial/circular:unknown-2024"
    - "bidding_untitled" → "bidding/forms/template:bidding-2024"
    """
    doc_type = metadata.get("document_type", "unknown")
    year = metadata.get("year") or "2024"
    number = metadata.get("number") or "unknown"
    
    taxonomy_map = {
        "law": f"legal/legislative/law:{number}-{year}",
        "decree": f"legal/executive/decree:{number}-{year}",
        "circular": f"legal/ministerial/circular:{number}-{year}",
        "decision": f"legal/executive/decision:{number}-{year}",
        "bidding": f"bidding/forms/template:{number}-{year}",
        "report": f"bidding/reports/template:{number}-{year}",
        "exam": f"training/assessments/exam:{number}-{year}"
    }
    
    return taxonomy_map.get(doc_type, f"other/{doc_type}/doc:{number}-{year}")
```

### Ưu điểm:
✅ Tổ chức rõ ràng theo category  
✅ Dễ query theo nhóm (tất cả legal/, tất cả bidding/)  
✅ Mở rộng dễ dàng với category mới  
✅ Phù hợp với file system structure  

### Nhược điểm:
❌ ID dài, phức tạp  
❌ Cần maintain taxonomy tree  
❌ Có thể conflict khi reorg taxonomy  

### Use cases phù hợp:
- ✅ Hệ thống lớn với nhiều category
- ✅ Cần organization rõ ràng
- ✅ Query theo nhóm document

---

## 🎯 OPTION 4: Hybrid System (Kết hợp ưu điểm các hệ thống)

### Cấu trúc:
```
{type_code}-{số_hiệu}/{năm}#{hash_short}
```

### Ví dụ:
- `ND-43/2022#a7f3c9` (Nghị định 43/2022/NĐ-CP)
- `TT-20/2020#b4d8e1` (Thông tư 20/2020)
- `QD-123/2021#c9a2d7` (Quyết định 123/2021)
- `FORM-17/2022#d5f8a3` (Mẫu số 17)
- `EXAM-01/2024#e1b9c4` (Đề thi 01)

### Migration logic:
```python
import hashlib

def migrate_to_hybrid_system(old_id: str, metadata: dict) -> str:
    """
    Kết hợp legal standard + hash để uniqueness
    
    Ví dụ:
    - "circular_untitled" → "TT-Unknown/2024#3f8a9c"
    - "decree_untitled" → "ND-Unknown/2024#5b2d7e"
    - "bidding_untitled" → "FORM-Bidding/2024#7c4e1a"
    """
    doc_type = metadata.get("document_type", "DOC")
    year = metadata.get("year") or "2024"
    number = metadata.get("number") or "Unknown"
    
    # Tạo hash ngắn từ old_id để uniqueness
    hash_obj = hashlib.md5(old_id.encode())
    hash_short = hash_obj.hexdigest()[:6]
    
    type_code_map = {
        "law": "LAW",
        "decree": "ND",
        "circular": "TT",
        "decision": "QD",
        "bidding": "FORM",
        "report": "RPT",
        "exam": "EXAM"
    }
    
    type_code = type_code_map.get(doc_type, "DOC")
    
    return f"{type_code}-{number}/{year}#{hash_short}"
```

### Ưu điểm:
✅ Vừa human-readable, vừa machine-friendly  
✅ Đảm bảo uniqueness với hash  
✅ Ngắn gọn hơn hierarchical  
✅ Tương thích với legal naming convention  

### Nhược điểm:
❌ Convention mới, cần training user  
❌ Hash suffix có thể gây confusion  

### Use cases phù hợp:
- ✅ Hệ thống vừa và lớn
- ✅ Cần balance giữa human-readable và uniqueness
- ✅ Có cả internal user và external API

---

## 📊 So sánh tổng quan

| Tiêu chí | Option 1 (Legal) | Option 2 (UUID) | Option 3 (Hierarchical) | Option 4 (Hybrid) |
|----------|------------------|-----------------|-------------------------|-------------------|
| **Human-readable** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Uniqueness** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Scalability** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Ease of migration** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Query performance** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Độ phức tạp** | Thấp | Thấp | Cao | Trung bình |
| **Phù hợp VN law** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 💡 Khuyến nghị

### Cho hệ thống của bạn, tôi khuyến nghị: **OPTION 4 (Hybrid System)**

**Lý do:**
1. ✅ **Tương thích với chuẩn pháp lý VN** - User dễ recognize
2. ✅ **Uniqueness đảm bảo** - Hash suffix tránh conflict
3. ✅ **Ngắn gọn** - Không dài dòng như hierarchical
4. ✅ **Migration dễ dàng** - Có thể extract metadata từ old_id
5. ✅ **Scalable** - Dễ thêm document type mới

### Migration strategy cho Option 4:

```python
# File: scripts/migrate_document_ids.py

import psycopg
import json
import hashlib
from datetime import datetime
from src.config.models import settings

def extract_metadata_from_old_id(old_id: str, metadata: dict) -> dict:
    """Extract hoặc infer metadata từ old_id và cmetadata"""
    
    # Lấy document_type từ metadata hoặc old_id
    doc_type = metadata.get("document_type")
    if not doc_type and old_id:
        if "bidding" in old_id:
            doc_type = "bidding"
        elif "circular" in old_id:
            doc_type = "circular"
        elif "decree" in old_id:
            doc_type = "decree"
        elif "law" in old_id:
            doc_type = "law"
        elif "exam" in old_id:
            doc_type = "exam"
        elif "report" in old_id:
            doc_type = "report"
    
    # Lấy year từ metadata hoặc timestamp
    year = metadata.get("year")
    if not year and metadata.get("processing_metadata"):
        processed_at = metadata["processing_metadata"].get("last_processed_at", "")
        if processed_at:
            year = processed_at[:4]
    if not year:
        year = "2024"
    
    # Lấy number từ document_id nếu có pattern số
    number = metadata.get("number") or "Unknown"
    
    return {
        "type": doc_type or "doc",
        "year": year,
        "number": number
    }

def generate_new_document_id(old_id: str, metadata: dict) -> str:
    """Generate new document_id theo Hybrid System"""
    
    extracted = extract_metadata_from_old_id(old_id, metadata)
    doc_type = extracted["type"]
    year = extracted["year"]
    number = extracted["number"]
    
    # Type code mapping
    type_code_map = {
        "law": "LAW",
        "decree": "ND",
        "circular": "TT",
        "decision": "QD",
        "bidding": "FORM",
        "report": "RPT",
        "exam": "EXAM"
    }
    
    type_code = type_code_map.get(doc_type, "DOC")
    
    # Generate hash từ old_id để đảm bảo uniqueness và idempotent
    hash_obj = hashlib.md5(old_id.encode())
    hash_short = hash_obj.hexdigest()[:6]
    
    new_id = f"{type_code}-{number}/{year}#{hash_short}"
    
    return new_id

def migrate_all_document_ids(dry_run=True):
    """
    Migrate tất cả document_ids trong database
    
    Args:
        dry_run: Nếu True, chỉ show preview không update
    """
    db_url = settings.database_url.replace("postgresql+psycopg", "postgresql")
    
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            # Lấy danh sách unique document_ids
            cur.execute("""
                SELECT DISTINCT cmetadata->>'document_id' as old_id
                FROM langchain_pg_embedding
                WHERE cmetadata->>'document_id' IS NOT NULL
            """)
            
            unique_docs = [row[0] for row in cur.fetchall()]
            
            print(f"Found {len(unique_docs)} unique documents to migrate\n")
            
            migration_map = {}
            
            for old_id in unique_docs:
                # Lấy metadata từ một chunk để generate new_id
                cur.execute("""
                    SELECT cmetadata
                    FROM langchain_pg_embedding
                    WHERE cmetadata->>'document_id' = %s
                    LIMIT 1
                """, (old_id,))
                
                metadata = cur.fetchone()[0]
                new_id = generate_new_document_id(old_id, metadata)
                
                migration_map[old_id] = new_id
                
                # Count chunks
                cur.execute("""
                    SELECT COUNT(*)
                    FROM langchain_pg_embedding
                    WHERE cmetadata->>'document_id' = %s
                """, (old_id,))
                
                chunk_count = cur.fetchone()[0]
                
                print(f"  {old_id:40s} → {new_id:30s} ({chunk_count:4d} chunks)")
            
            if dry_run:
                print(f"\n🔍 DRY RUN - Không có thay đổi nào được apply")
                print(f"Để thực hiện migration thật, chạy: migrate_all_document_ids(dry_run=False)")
                return migration_map
            
            # Apply migration
            print(f"\n🚀 Bắt đầu migration...")
            
            total_updated = 0
            for old_id, new_id in migration_map.items():
                # Update tất cả chunks của document này
                cur.execute("""
                    UPDATE langchain_pg_embedding
                    SET cmetadata = jsonb_set(
                        cmetadata,
                        '{document_id}',
                        to_jsonb(%s::text)
                    )
                    WHERE cmetadata->>'document_id' = %s
                """, (new_id, old_id))
                
                updated_count = cur.rowcount
                total_updated += updated_count
            
            conn.commit()
            
            print(f"\n✅ Migration hoàn thành!")
            print(f"   Đã cập nhật {total_updated} chunks")
            print(f"   Cho {len(migration_map)} documents")
            
            return migration_map

if __name__ == "__main__":
    # Dry run trước
    print("="*80)
    print("DRY RUN - Preview migration")
    print("="*80)
    migrate_all_document_ids(dry_run=True)
```

### Sử dụng:

```bash
# 1. Preview migration (dry run)
python scripts/migrate_document_ids.py

# 2. Thực hiện migration thật
python -c "from scripts.migrate_document_ids import migrate_all_document_ids; migrate_all_document_ids(dry_run=False)"
```

---

## 🔮 Future-proof: Thêm văn bản mới

Sau khi migrate, khi thêm văn bản mới, document_id sẽ được tạo tự động:

```python
# Trong preprocessing pipeline
def generate_document_id_for_new_doc(file_path: str, doc_type: str) -> str:
    """
    Generate document_id cho văn bản mới khi upload
    
    Logic:
    1. Parse filename để extract số hiệu, năm
    2. Nếu không parse được → dùng timestamp + hash
    3. Generate theo Hybrid System
    """
    import re
    from datetime import datetime
    
    filename = Path(file_path).stem
    
    # Pattern matching cho các loại văn bản VN
    patterns = {
        "decree": r"(\d+)[-/](\d{4})[-/](?:NĐ|ND)",
        "circular": r"(\d+)[-/](\d{4})[-/]TT",
        "decision": r"(\d+)[-/](\d{4})[-/](?:QĐ|QD)",
        "law": r"Luật.*(\d+)[-/](\d{4})",
    }
    
    number = None
    year = None
    
    # Try to extract từ filename
    if doc_type in patterns:
        match = re.search(patterns[doc_type], filename, re.IGNORECASE)
        if match:
            number = match.group(1)
            year = match.group(2)
    
    # Fallback: use timestamp
    if not number:
        number = datetime.now().strftime("%Y%m%d%H%M%S")
    if not year:
        year = datetime.now().strftime("%Y")
    
    # Generate hash từ file_path để uniqueness
    hash_obj = hashlib.md5(file_path.encode())
    hash_short = hash_obj.hexdigest()[:6]
    
    type_code_map = {
        "law": "LAW",
        "decree": "ND",
        "circular": "TT",
        "decision": "QD",
        "bidding": "FORM",
        "report": "RPT",
        "exam": "EXAM"
    }
    
    type_code = type_code_map.get(doc_type, "DOC")
    
    return f"{type_code}-{number}/{year}#{hash_short}"
```

---

## Bạn muốn option nào?

Hãy cho tôi biết bạn chọn option nào (1-4) hoặc cần customize thêm!
