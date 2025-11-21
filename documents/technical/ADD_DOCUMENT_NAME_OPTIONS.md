# Options để thêm Document Name vào Metadata

## 📊 Phân tích hiện trạng

### Data có sẵn:
1. ✅ **Metadata files** (`data/processed/metadata/*.json`):
   - Có `source_file`: `"data/raw/Ho so moi thau/6. Tư vấn/6. Mẫu số 6C_E-TVCN tư vấn cá nhân.docx"`
   - Có `category`: `"6. Tư vấn"`
   - Có mapping chunk_count, output_file

2. ❌ **Chunks** (`data/processed/chunks/*.jsonl`):
   - KHÔNG có `source_file`
   - KHÔNG có `document_name`

3. ❌ **Database** (langchain_pg_embedding):
   - `cmetadata` KHÔNG có `source_file`
   - `cmetadata` KHÔNG có `document_name`

### Document ID mapping:
```
chunk_id: "bidding_untitled_form_0102"
document_id: "FORM-Bidding/2025#bee720"
source_file: "data/raw/Ho so moi thau/..." (MISSING in DB)
```

---

## 🎯 OPTIONS - Từ nhanh → toàn diện

### **OPTION 1: Quick Patch - Extract từ chunk_id (15 phút)** ⚡
**Cách làm**: Parse document name từ `chunk_id` pattern

**Ưu điểm**:
- Nhanh nhất, không cần đọc file
- Không cần migrate data
- Chỉ sửa 1 function trong API

**Nhược điểm**:
- Tên không chính xác (ví dụ: "bidding_untitled_form" thay vì tên file thật)
- Phụ thuộc vào naming convention

**Implementation**:
```python
# src/api/routers/documents_management.py

def extract_title_from_metadata(cmetadata: dict) -> str:
    """Extract title từ chunk_id pattern"""
    chunk_id = cmetadata.get("chunk_id", "")
    
    # Pattern: {type}_{doc_name}_{section}_{index}
    # Example: "bidding_untitled_form_0102"
    parts = chunk_id.split("_")
    if len(parts) >= 3:
        doc_type = parts[0]  # "bidding"
        doc_name = "_".join(parts[1:-1])  # "untitled_form"
        
        # Clean up
        doc_name = doc_name.replace("_", " ").title()
        return f"{doc_type.title()}: {doc_name}"
    
    # Fallback
    return cmetadata.get("section_title", "Unknown Document")[:100]
```

**Result**: `"Bidding: Untitled Form"` (không đẹp lắm)

---

### **OPTION 2: Mapping Table - Tạo document_id → name lookup (30 phút)** 📋
**Cách làm**: Tạo mapping dict từ metadata files, store trong code hoặc file

**Ưu điểm**:
- Tên chính xác từ source file
- Không cần migrate database
- Dễ maintain và update

**Nhược điểm**:
- Cần build mapping table trước
- Phải update khi có document mới

**Implementation**:

**Step 1**: Build mapping table
```python
# scripts/build_document_name_mapping.py

import json
import glob
from pathlib import Path

def build_mapping():
    """Build document_id -> document_name mapping"""
    mapping = {}
    
    # Read all metadata files
    for meta_file in glob.glob("data/processed/metadata/*.json"):
        with open(meta_file) as f:
            meta = json.load(f)
        
        source_file = meta.get("source_file", "")
        if not source_file:
            continue
        
        # Extract document name from source_file
        # "data/raw/Ho so moi thau/6. Tư vấn/6. Mẫu số 6C_E-TVCN tư vấn cá nhân.docx"
        # → "6. Mẫu số 6C_E-TVCN tư vấn cá nhân"
        doc_name = Path(source_file).stem
        
        # Find matching chunks to get document_id
        chunk_file = meta.get("output_file", "")
        if chunk_file:
            # Read first chunk to get document_id
            with open(chunk_file) as cf:
                first_chunk = json.loads(cf.readline())
                doc_id = first_chunk.get("document_id")
                
                if doc_id:
                    mapping[doc_id] = {
                        "name": doc_name,
                        "category": meta.get("category", ""),
                        "source_file": source_file,
                        "document_type": meta.get("document_type", "")
                    }
    
    # Save mapping
    with open("src/config/document_name_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created mapping for {len(mapping)} documents")
    return mapping

if __name__ == "__main__":
    build_mapping()
```

**Step 2**: Use mapping in API
```python
# src/api/routers/documents_management.py

import json
from pathlib import Path

# Load mapping once at startup
MAPPING_FILE = Path(__file__).parent.parent.parent / "config" / "document_name_mapping.json"
DOCUMENT_NAME_MAPPING = {}

try:
    with open(MAPPING_FILE) as f:
        DOCUMENT_NAME_MAPPING = json.load(f)
except FileNotFoundError:
    logger.warning("Document name mapping not found. Run build_document_name_mapping.py")

def extract_title_from_metadata(cmetadata: dict) -> str:
    """Extract title using mapping table"""
    document_id = cmetadata.get("document_id")
    
    # Try mapping first
    if document_id and document_id in DOCUMENT_NAME_MAPPING:
        return DOCUMENT_NAME_MAPPING[document_id]["name"]
    
    # Fallback: section_title
    section_title = cmetadata.get("section_title", "")
    if section_title and len(section_title) < 100:
        return section_title
    
    # Last resort: truncate hierarchy
    if "hierarchy" in cmetadata:
        try:
            hierarchy = json.loads(cmetadata["hierarchy"])
            if hierarchy:
                return hierarchy[0][:100] + ("..." if len(hierarchy[0]) > 100 else "")
        except:
            pass
    
    return f"Document {document_id}"
```

**Result**: `"6. Mẫu số 6C_E-TVCN tư vấn cá nhân"` (chính xác!)

---

### **OPTION 3: Backfill Database - Update metadata trong DB (1 giờ)** 🔄
**Cách làm**: Update tất cả records trong database để thêm `document_name`

**Ưu điểm**:
- Data đầy đủ, không cần lookup
- Permanent solution
- Dễ query và filter

**Nhược điểm**:
- Mất thời gian chạy migration
- Cần test kỹ
- Phải reprocess nếu có lỗi

**Implementation**:

**Step 1**: Build update mapping (giống Option 2)
```python
# scripts/migrate_add_document_name.py

import json
import glob
import asyncio
from pathlib import Path
from sqlalchemy import text
from src.config.database import get_session

async def build_document_name_mapping():
    """Same as Option 2"""
    mapping = {}
    
    for meta_file in glob.glob("data/processed/metadata/*.json"):
        with open(meta_file) as f:
            meta = json.load(f)
        
        source_file = meta.get("source_file", "")
        doc_name = Path(source_file).stem if source_file else ""
        
        chunk_file = meta.get("output_file", "")
        if chunk_file and Path(chunk_file).exists():
            with open(chunk_file) as cf:
                first_chunk = json.loads(cf.readline())
                doc_id = first_chunk.get("document_id")
                
                if doc_id:
                    mapping[doc_id] = {
                        "name": doc_name,
                        "category": meta.get("category", ""),
                        "source_file": source_file
                    }
    
    return mapping

async def update_database():
    """Update all chunks in database"""
    mapping = await build_document_name_mapping()
    
    async for db in get_session():
        try:
            # Get all unique document_ids
            result = await db.execute(
                text("SELECT DISTINCT cmetadata->>'document_id' as doc_id FROM langchain_pg_embedding")
            )
            doc_ids = [row[0] for row in result.fetchall()]
            
            updated_count = 0
            for doc_id in doc_ids:
                if doc_id not in mapping:
                    print(f"⚠️  No mapping for {doc_id}")
                    continue
                
                doc_info = mapping[doc_id]
                
                # Update all chunks for this document
                await db.execute(
                    text("""
                        UPDATE langchain_pg_embedding
                        SET cmetadata = jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    cmetadata,
                                    '{document_name}',
                                    :doc_name
                                ),
                                '{source_file}',
                                :source_file
                            ),
                            '{category}',
                            :category
                        )
                        WHERE cmetadata->>'document_id' = :doc_id
                    """),
                    {
                        "doc_id": doc_id,
                        "doc_name": json.dumps(doc_info["name"]),
                        "source_file": json.dumps(doc_info["source_file"]),
                        "category": json.dumps(doc_info["category"])
                    }
                )
                
                updated_count += 1
                print(f"✅ Updated {doc_id}: {doc_info['name']}")
            
            await db.commit()
            print(f"\n🎉 Updated {updated_count}/{len(doc_ids)} documents")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(update_database())
```

**Step 2**: Update API to use new field
```python
# src/api/routers/documents_management.py

def extract_title_from_metadata(cmetadata: dict) -> str:
    """Extract title from metadata (now has document_name!)"""
    # NEW: Use document_name field
    if "document_name" in cmetadata and cmetadata["document_name"]:
        return cmetadata["document_name"]
    
    # Fallback: section_title
    return cmetadata.get("section_title", f"Document {cmetadata.get('document_id', 'Unknown')}")[:100]
```

**Result**: `"6. Mẫu số 6C_E-TVCN tư vấn cá nhân"` (permanent!)

---

### **OPTION 4: Reprocess Pipeline - Update preprocessing (3 giờ)** 🏗️
**Cách làm**: Sửa preprocessing pipeline để luôn lưu `document_name` trong chunks

**Ưu điểm**:
- Solution lâu dài nhất
- Tất cả document mới sẽ có `document_name`
- Chuẩn hóa data structure

**Nhược điểm**:
- Mất nhiều thời gian nhất
- Phải reprocess ALL documents
- Cần test thoroughly

**Implementation**:

**Step 1**: Update chunk processing
```python
# src/preprocessing/base_processor.py (hoặc file tương tự)

class DocumentProcessor:
    def process_document(self, file_path: str, **kwargs):
        """Process document and include source metadata"""
        
        # Extract document name from file path
        doc_name = Path(file_path).stem
        category = self._extract_category(file_path)
        
        # Process chunks
        chunks = self._split_into_chunks(file_path)
        
        for chunk in chunks:
            # ADD document_name and source_file to EVERY chunk
            chunk["document_name"] = doc_name
            chunk["source_file"] = file_path
            chunk["category"] = category
            
            yield chunk
    
    def _extract_category(self, file_path: str) -> str:
        """Extract category from folder structure"""
        # "data/raw/Ho so moi thau/6. Tư vấn/file.docx"
        # → "6. Tư vấn"
        parts = Path(file_path).parts
        if len(parts) >= 3:
            return parts[-2]  # Parent folder
        return "Unknown"
```

**Step 2**: Reprocess all documents
```bash
# Backup current data first!
cp -r data/processed data/processed_backup_$(date +%Y%m%d)

# Reprocess
python scripts/batch_reprocess_all.py

# Reimport to database
python scripts/import_processed_chunks.py
```

**Result**: All future documents will have proper names automatically

---

## 📊 Comparison Matrix

| Option | Time | Accuracy | Permanent | Complexity | Recommended |
|--------|------|----------|-----------|------------|-------------|
| **1. Quick Patch** | 15 min | ⭐⭐ | ❌ | ⭐ | Testing only |
| **2. Mapping Table** | 30 min | ⭐⭐⭐⭐⭐ | ✅ (in code) | ⭐⭐ | **YES - Best balance** |
| **3. Backfill DB** | 1 hour | ⭐⭐⭐⭐⭐ | ✅ (in DB) | ⭐⭐⭐ | If need DB queries |
| **4. Reprocess** | 3 hours | ⭐⭐⭐⭐⭐ | ✅ (everywhere) | ⭐⭐⭐⭐⭐ | Long-term only |

---

## 🎯 Recommendation: **OPTION 2 + OPTION 3**

### Phase 1: Quick Win (30 phút)
1. Implement **Option 2** (Mapping Table)
   - Run `build_document_name_mapping.py`
   - Update API to use mapping
   - Test immediately

### Phase 2: Solidify (1 giờ)
2. Run **Option 3** (Backfill Database)
   - Migrate data to add `document_name` field
   - Update API to prefer DB field over mapping
   - Keep mapping as fallback

### Phase 3: Future-proof (sau này)
3. Update preprocessing pipeline (Option 4)
   - Only for new documents
   - No need to reprocess existing

---

## 🚀 Quick Start (Option 2)

```bash
# 1. Build mapping
python scripts/build_document_name_mapping.py

# 2. Restart server
./start_server.sh

# 3. Test
curl "http://localhost:8000/api/documents/catalog?limit=5" | jq '.[].title'
```

Expected output:
```
"6. Mẫu số 6C_E-TVCN tư vấn cá nhân"
"14A. Mẫu BCĐG PTV HH XL hop hop TBYT CGTT. quy trình 1_1 tui"
...
```

---

## ⚠️ Notes

1. **Encoding**: Ensure UTF-8 for Vietnamese characters
2. **Missing mappings**: Some documents might not have metadata files
3. **Backup**: Always backup before Option 3 or 4
4. **Testing**: Test with small batch first

---

## 📝 Next Steps

Sau khi implement xong, có thể:
1. Add API endpoint để manage document names
2. Add search by document name
3. Add filter by category
4. Export document catalog to Excel
