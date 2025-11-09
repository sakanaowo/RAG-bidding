# Tóm tắt: Document Status API & Document ID Migration

## ✅ Đã hoàn thành

### 1. Cập nhật API Prefix

**Trước:**
- Upload API: `/api/upload/*`
- Document Status API: `/api/v1/document-status/*`

**Sau:**
- Upload API: `/api/upload/*`
- Document Status API: `/api/document-status/*`

**Files đã sửa:**
- `src/api/main.py` - Thay đổi prefix từ `/api/v1` → `/api`

**Endpoints hiện tại:**
```
POST /api/document-status/update       - Cập nhật status văn bản
GET  /api/document-status/{document_id} - Lấy thông tin status
```

---

## 📋 Đề xuất Document ID System

Đã phân tích **4 options** cho Document ID system (chi tiết trong `documents/DOCUMENT_ID_PROPOSAL.md`):

### Option 1: Legal Document Standard ID
```
Format: {số_hiệu}/{năm}/{loại_văn_bản}
Ví dụ: 43/2022/NĐ-CP, 20/2020/TT-BTC
```
- ✅ Tuân thủ chuẩn pháp lý VN
- ❌ Khó xử lý văn bản không có số hiệu

### Option 2: UUID-based System
```
Format: {type}_{year}_{uuid_short}
Ví dụ: decree_2024_a7f3c9e2, circular_2023_b4d8e1f5
```
- ✅ Uniqueness tuyệt đối
- ❌ Không human-readable

### Option 3: Hierarchical System
```
Format: {category}/{subcategory}/{type}:{number}-{year}
Ví dụ: legal/executive/decree:43-2022
```
- ✅ Tổ chức rõ ràng theo taxonomy
- ❌ ID dài, phức tạp

### Option 4: Hybrid System ⭐ **RECOMMENDED**
```
Format: {type_code}-{số_hiệu}/{năm}#{hash_short}
Ví dụ: ND-43/2022#a7f3c9, TT-20/2020#b4d8e1
```
- ✅ Vừa human-readable, vừa machine-friendly
- ✅ Đảm bảo uniqueness với hash
- ✅ Tương thích với legal naming convention
- ✅ Migration dễ dàng

**Type codes:**
- `LAW` - Luật
- `ND` - Nghị định
- `TT` - Thông tư
- `QD` - Quyết định
- `FORM` - Mẫu hồ sơ (bidding templates)
- `RPT` - Báo cáo
- `EXAM` - Đề thi

---

## 🔄 Migration Preview

Script migration đã sẵn sàng: `scripts/migrate_document_ids.py`

**Preview kết quả migration:**

| STT | Document Type | Old ID | New ID | Chunks |
|-----|---------------|--------|--------|--------|
| 1 | bidding | `bidding_untitled` | `FORM-Bidding/2025#bee720` | 2831 |
| 2 | circular | `circular_untitled` | `TT-Circular/2025#3be8b6` | 123 |
| 3 | decision | `decision_untitled` | `QD-Decision/2025#787999` | 5 |
| 4 | decree | `decree_untitled` | `ND-Decree/2025#95b863` | 595 |
| 5 | law | `law_untitled` | `LAW-Law/2025#cd5116` | 1154 |

**Tổng cộng:**
- 5 documents
- 4708 chunks

---

## 🚀 Cách sử dụng

### 1. Preview migration (không thay đổi database)
```bash
python scripts/migrate_document_ids.py
```

### 2. Execute migration (cập nhật database)
```bash
python scripts/migrate_document_ids.py --execute
```

### 3. Test API sau khi migrate
```bash
# Old ID (vẫn hoạt động trước khi migrate)
curl http://localhost:8000/api/document-status/bidding_untitled

# New ID (sau khi migrate)
curl http://localhost:8000/api/document-status/FORM-Bidding/2025%23bee720
```

---

## 📝 Future: Thêm văn bản mới

Khi thêm văn bản mới, document_id sẽ được tạo tự động theo logic:

```python
def generate_document_id_for_new_doc(file_path: str, doc_type: str) -> str:
    """
    Generate document_id cho văn bản mới
    
    Logic:
    1. Parse filename để extract số hiệu, năm
       Ví dụ: "43-2022-ND-CP.pdf" → số=43, năm=2022
    
    2. Nếu không parse được → dùng timestamp
       Ví dụ: số=20251109151030
    
    3. Generate theo format: {type_code}-{số}/{năm}#{hash}
       Ví dụ: ND-43/2022#a7f3c9
    """
    # Implementation trong preprocessing pipeline
```

**Patterns hỗ trợ:**
- Nghị định: `43-2022-ND-CP.pdf` → `ND-43/2022#xxxxx`
- Thông tư: `20-2020-TT-BTC.pdf` → `TT-20/2020#xxxxx`
- Quyết định: `123-2021-QD-TTg.pdf` → `QD-123/2021#xxxxx`
- Luật: `Luat-Xay-dung-2020.pdf` → `LAW-59/2020#xxxxx`

---

## ⚠️ Lưu ý

1. **Backup database** trước khi execute migration
2. Migration là **idempotent** (chạy nhiều lần → kết quả giống nhau)
3. Hash được generate từ old_id → đảm bảo consistency
4. API vẫn hoạt động bình thường sau migration
5. Có thể rollback bằng cách restore backup

---

## 📚 Tài liệu tham khảo

- Chi tiết 4 options: `documents/DOCUMENT_ID_PROPOSAL.md`
- Migration script: `scripts/migrate_document_ids.py`
- API implementation: `src/api/routers/document_status.py`
- Service logic: `src/api/services/document_status.py`
