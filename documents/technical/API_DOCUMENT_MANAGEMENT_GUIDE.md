# 📘 Document Management API - Postman Guide

**New API:** Document-level operations (not chunk-level)  
**Base URL:** `http://localhost:8000/api/documents/catalog`

---

## 🎯 Key Differences

| Feature | `/api/documents` (OLD) | `/api/documents/catalog` (NEW) |
|---------|----------------------|-------------------------------|
| **Returns** | Individual CHUNKS | Complete DOCUMENTS |
| **Grouping** | No grouping | Grouped by `document_id` |
| **Title** | ❌ Missing | ✅ Extracted from hierarchy |
| **Total Chunks** | ❌ Not shown | ✅ Aggregated count |
| **Status Update** | Single chunk only | ALL chunks in document |
| **Use Case** | Retrieval results | Document management |

---

## 📚 1. Get Document Catalog (List Documents)

### Request
```http
GET /api/documents/catalog?limit=10&offset=0
```

### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max documents (≤200) |
| `offset` | int | 0 | Pagination offset |
| `document_type` | string | - | Filter: `law`, `decree`, `bidding` |
| `status` | string | - | Filter: `active`, `superseded` |

### Response
```json
[
    {
        "document_id": "FORM-Bidding/2025#bee720",
        "title": "Mẫu số 17",
        "document_type": "bidding",
        "total_chunks": 104,
        "status": "active",
        "published_date": null,
        "effective_date": null,
        "last_modified": "2025-11-09T14:06:20.876510",
        "hierarchy_path": ["Mẫu số 17"],
        "chunk_ids": ["646f799a-...", "7a2b..."]
    }
]
```

### Postman Setup
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents/catalog`
3. Params:
   - `limit`: `10`
   - `document_type`: `bidding` (optional)
4. Send

---

## 📄 2. Get Full Document Details

### Request
```http
GET /api/documents/catalog/{document_id}
```

### Example
```http
GET /api/documents/catalog/FORM-Bidding/2025#bee720
```

### Response
```json
{
    "document_id": "FORM-Bidding/2025#bee720",
    "title": "Mẫu số 17",
    "document_type": "bidding",
    "total_chunks": 104,
    "status": "active",
    "metadata": {
        "document_id": "FORM-Bidding/2025#bee720",
        "document_type": "bidding",
        "hierarchy": "[\"Mẫu số 17\"]",
        "total_chunks": 104,
        "processing_metadata": {...}
    },
    "chunks": [
        {
            "chunk_id": "646f799a-8e02-4e1f-a317-235daaa2c176",
            "chunk_index": 0,
            "content": "[Section: IV. Tổng hợp giá dự thầu]...",
            "metadata": {...}
        },
        {
            "chunk_id": "7a2b...",
            "chunk_index": 1,
            "content": "...",
            "metadata": {...}
        }
    ],
    "status_history": [
        {
            "from_status": "active",
            "to_status": "superseded",
            "reason": "Mẫu hồ sơ mới đã được ban hành",
            "timestamp": "2025-11-09T15:06:59.284102",
            "changed_by": "api"
        }
    ]
}
```

### Postman Setup
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents/catalog/{{document_id}}`
3. Environment variable:
   - `document_id`: `FORM-Bidding/2025#bee720`
4. Send

---

## 📊 3. Get Document Statistics

### Request
```http
GET /api/documents/catalog/{document_id}/stats
```

### Response
```json
{
    "document_id": "FORM-Bidding/2025#bee720",
    "total_chunks": 104,
    "total_characters": 210000,
    "avg_chunk_size": 2019.2,
    "has_tables": 15,
    "has_lists": 8,
    "hierarchy_levels": ["Mẫu số 17"],
    "concepts": [
        "chủ đầu tư",
        "nhà thầu",
        "thời gian thực hiện",
        "gói thầu"
    ]
}
```

### Postman Setup
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents/catalog/{{document_id}}/stats`
3. Send

---

## ✏️ 4. Update Document Status (ALL Chunks)

### Request
```http
PATCH /api/documents/catalog/{document_id}/status
Content-Type: application/json

{
    "status": "active",
    "reason": "Document is now in effect"
}
```

### Supported Status Values
- `draft` - Tài liệu đang soạn thảo
- `active` - Tài liệu đang hiệu lực ✅ (default)
- `superseded` - Tài liệu đã bị thay thế
- `archived` - Tài liệu đã lưu trữ

### Response
```json
{
    "success": true,
    "document_id": "FORM-Bidding/2025#bee720",
    "old_status": "draft",
    "new_status": "active",
    "reason": "Document is now in effect",
    "updated_at": "2025-11-14T21:45:00",
    "chunks_updated": 104
}
```

### Postman Setup
1. Method: `PATCH`
2. URL: `http://localhost:8000/api/documents/catalog/{{document_id}}/status`
3. Headers:
   - `Content-Type`: `application/json`
4. Body → raw → JSON:
```json
{
    "status": "active",
    "reason": "Testing document status update"
}
```
5. Send

---

## 🚀 Complete Postman Workflow

### Step 1: Get Document Catalog
```
Request: GET /api/documents/catalog?document_type=bidding&limit=5
→ Copy document_id from first result
```

### Step 2: Save as Environment Variable
```
Environment: Local RAG
Variable: document_id
Value: FORM-Bidding/2025#bee720
```

### Step 3: Get Full Document
```
Request: GET /api/documents/catalog/{{document_id}}
→ See all 104 chunks, title, status history
```

### Step 4: Update Status to Active
```
Request: PATCH /api/documents/catalog/{{document_id}}/status
Body: {"status": "active", "reason": "Testing"}
→ All 104 chunks updated
```

### Step 5: Verify Update
```
Request: GET /api/documents/catalog/{{document_id}}
→ Check status = "active"
→ Check status_history has new entry
```

### Step 6: Toggle Status
```
Request: PATCH /api/documents/catalog/{{document_id}}/status
Body: {"status": "superseded", "reason": "Replaced by new version"}
→ All 104 chunks updated again
```

### Step 7: Get Statistics
```
Request: GET /api/documents/catalog/{{document_id}}/stats
→ See total chunks, characters, tables, concepts
```

---

## 📋 Postman Collection JSON

Import this into Postman:

```json
{
    "info": {
        "name": "RAG Document Management",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "1. Get Document Catalog",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/documents/catalog?limit=10&document_type=bidding",
                    "host": ["{{base_url}}"],
                    "path": ["documents", "catalog"],
                    "query": [
                        {"key": "limit", "value": "10"},
                        {"key": "document_type", "value": "bidding"}
                    ]
                }
            }
        },
        {
            "name": "2. Get Document Details",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/documents/catalog/{{document_id}}",
                    "host": ["{{base_url}}"],
                    "path": ["documents", "catalog", "{{document_id}}"]
                }
            }
        },
        {
            "name": "3. Get Document Stats",
            "request": {
                "method": "GET",
                "header": [],
                "url": {
                    "raw": "{{base_url}}/documents/catalog/{{document_id}}/stats",
                    "host": ["{{base_url}}"],
                    "path": ["documents", "catalog", "{{document_id}}", "stats"]
                }
            }
        },
        {
            "name": "4. Update Status to Active",
            "request": {
                "method": "PATCH",
                "header": [
                    {"key": "Content-Type", "value": "application/json"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"status\": \"active\",\n    \"reason\": \"Document is now in effect\"\n}"
                },
                "url": {
                    "raw": "{{base_url}}/documents/catalog/{{document_id}}/status",
                    "host": ["{{base_url}}"],
                    "path": ["documents", "catalog", "{{document_id}}", "status"]
                }
            }
        },
        {
            "name": "5. Update Status to Superseded",
            "request": {
                "method": "PATCH",
                "header": [
                    {"key": "Content-Type", "value": "application/json"}
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n    \"status\": \"superseded\",\n    \"reason\": \"Replaced by newer version\"\n}"
                },
                "url": {
                    "raw": "{{base_url}}/documents/catalog/{{document_id}}/status",
                    "host": ["{{base_url}}"],
                    "path": ["documents", "catalog", "{{document_id}}", "status"]
                }
            }
        }
    ],
    "variable": [
        {
            "key": "base_url",
            "value": "http://localhost:8000/api"
        },
        {
            "key": "document_id",
            "value": "FORM-Bidding/2025#bee720"
        }
    ]
}
```

---

## 🔍 Comparison: OLD vs NEW API

### Get Document Information

**OLD API (Chunk-level):**
```http
GET /api/documents/646f799a-8e02-4e1f-a317-235daaa2c176
→ Returns: 1 chunk only
→ Title: ❌ null
→ Total chunks: ❌ unknown
→ Status update: Only this chunk
```

**NEW API (Document-level):**
```http
GET /api/documents/catalog/FORM-Bidding/2025#bee720
→ Returns: Full document (104 chunks)
→ Title: ✅ "Mẫu số 17"
→ Total chunks: ✅ 104
→ Status update: All 104 chunks
```

### Update Status

**OLD API:**
```http
PATCH /api/documents/646f799a-8e02-4e1f-a317-235daaa2c176/status
→ Updates: 1 chunk only ❌
→ Other 103 chunks unchanged ❌
```

**NEW API:**
```http
PATCH /api/documents/catalog/FORM-Bidding/2025#bee720/status
→ Updates: ALL 104 chunks ✅
→ Consistent status across document ✅
```

---

## 🎯 When to Use Which API

| Use Case | API to Use | Reason |
|----------|-----------|--------|
| Show retrieval results | `/api/documents` | Returns chunks for search |
| Manage documents | `/api/documents/catalog` | Document-level operations |
| Update document status | `/api/documents/catalog/{id}/status` | Updates all chunks |
| Get document title | `/api/documents/catalog` | Title extracted |
| View all chunks | `/api/documents/catalog/{id}` | Full document view |
| Filter by status | `/api/documents/catalog?status=active` | Document-level filter |

---

## ✅ Testing Checklist

- [ ] Get catalog → See documents grouped by `document_id`
- [ ] Get document details → See title, 104 chunks, status history
- [ ] Get statistics → See total characters, tables, concepts
- [ ] Update status to "active" → Verify `chunks_updated: 104`
- [ ] Get document again → Verify status changed
- [ ] Check status_history → See new entry added
- [ ] Toggle to "superseded" → Verify all chunks updated
- [ ] Filter by type → Get only bidding documents
- [ ] Filter by status → Get only active/superseded docs

---

**Created:** 2025-11-14  
**Last Updated:** 2025-11-14  
**API Version:** 2.0.0  
**Server:** http://localhost:8000
