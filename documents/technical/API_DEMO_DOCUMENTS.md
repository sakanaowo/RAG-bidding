# 📘 Document Endpoints - Demo Guide & Postman Examples

## 🎯 Overview

API endpoints để quản lý tài liệu trong database. Bao gồm:
- ✅ Get statistics
- ✅ List documents với filters & pagination
- ✅ Get specific document by ID
- ✅ Update document status
- ✅ Metadata filtering (type, status, dieu, khoan)

**Base URL:** `http://localhost:8000/api`

---

## 📊 1. Get Document Statistics

### Request
```http
GET /api/documents/stats/summary
```

### Response Example
```json
{
    "total_documents": 4708,
    "by_type": {
        "bidding": 2831,
        "law": 1154,
        "decree": 595,
        "circular": 123,
        "decision": 5
    },
    "by_status": {
        "null": 4708
    }
}
```

### Postman Setup
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents/stats/summary`
3. Headers: None needed
4. Click **Send**

---

## 📄 2. List Documents (With Filters)

### Request - Basic List
```http
GET /api/documents?limit=10&offset=0
```

### Request - With Filters
```http
GET /api/documents?document_type=law&limit=5
GET /api/documents?status=active&limit=10
GET /api/documents?dieu=29&document_type=law
```

### Query Parameters
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `limit` | int | Max records (default: 50) | `10` |
| `offset` | int | Skip N records (default: 0) | `20` |
| `document_type` | string | Filter by type | `law`, `decree`, `bidding` |
| `status` | string | Filter by status | `active`, `superseded`, `draft` |
| `dieu` | string | Filter by dieu number | `29` |
| `khoan` | string | Filter by khoan number | `1` |

### Response Example (Actual Data from DB)
```json
[
    {
        "id": "21cb377c-405d-4301-a666-23317f4332d1",
        "document_id": "DOC-Document/2025#787999",
        "title": null,
        "document_type": "decision",
        "chuong": null,
        "dieu": null,
        "khoan": null,
        "diem": null,
        "page_content": "[Section: Điều 1. Quyết định này quy định việc áp dụng hình thức lựa chọn nhà thầu trong trường hợp đặc biệt...]\n\nĐiều 1. Quyết định này quy định việc áp dụng hình thức lựa chọn nhà thầu trong trường hợp đặc biệt theo quy định tại điểm đ khoản 1 Điều 29 Luật Đấu thầu số 22/2023/QH15 đối với:\n1. Gói thầu về đào tạo chuyên sâu cho cơ quan nhà nước...",
        "published_date": null,
        "effective_date": null,
        "status": null,
        "url": null
    }
]
```

### Postman Setup - List All
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents`
3. Params tab:
   - `limit`: `10`
   - `offset`: `0`
4. Click **Send**

### Postman Setup - Filter by Type
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents`
3. Params tab:
   - `document_type`: `law`
   - `limit`: `5`
4. Click **Send**

---

## 🔍 3. Get Single Document by ID

### Request
```http
GET /api/documents/{document_id}
```

### Example with Real ID
```http
GET /api/documents/21cb377c-405d-4301-a666-23317f4332d1
```

### Response
```json
{
    "id": "21cb377c-405d-4301-a666-23317f4332d1",
    "document_id": "DOC-Document/2025#787999",
    "title": null,
    "document_type": "decision",
    "chuong": null,
    "dieu": null,
    "khoan": null,
    "diem": null,
    "page_content": "...",
    "published_date": null,
    "effective_date": null,
    "status": null,
    "url": null
}
```

### Postman Setup
1. Method: `GET`
2. URL: `http://localhost:8000/api/documents/21cb377c-405d-4301-a666-23317f4332d1`
3. Click **Send**

---

## ✏️ 4. Update Document Status

### Request
```http
PATCH /api/documents/{document_id}/status
Content-Type: application/json

{
    "status": "active",
    "reason": "Testing status update"
}
```

### Supported Status Values
- `draft` - Tài liệu đang soạn thảo
- `active` - Tài liệu đang hiệu lực
- `superseded` - Tài liệu đã bị thay thế
- `archived` - Tài liệu đã lưu trữ

### Example with Real ID
```http
PATCH /api/documents/21cb377c-405d-4301-a666-23317f4332d1/status
Content-Type: application/json

{
    "status": "active",
    "reason": "Document is now in effect"
}
```

### Response
```json
{
    "success": true,
    "document_id": "21cb377c-405d-4301-a666-23317f4332d1",
    "old_status": null,
    "new_status": "active",
    "reason": "Document is now in effect",
    "updated_at": "2025-11-14T20:45:00",
    "metadata": {
        "status_change_history": [
            {
                "from_status": null,
                "to_status": "active",
                "reason": "Document is now in effect",
                "timestamp": "2025-11-14T20:45:00",
                "changed_by": "api"
            }
        ]
    }
}
```

---

## 🚀 Postman Collection - Step by Step

### Step 1: Create New Request - Get Statistics
```
1. Click "New" → "Request"
2. Name: "Get Document Stats"
3. Collection: Create "RAG Bidding API"
4. Method: GET
5. URL: http://localhost:8000/api/documents/stats/summary
6. Save & Send
```

### Step 2: Get First Document
```
1. New Request: "List Documents"
2. Method: GET
3. URL: http://localhost:8000/api/documents
4. Params:
   - limit: 1
   - offset: 0
5. Send
6. Copy "id" from response (e.g., 21cb377c-405d-4301-a666-23317f4332d1)
```

### Step 3: Get Specific Document
```
1. New Request: "Get Document by ID"
2. Method: GET
3. URL: http://localhost:8000/api/documents/{{document_id}}
4. Create variable:
   - Collection → Variables
   - Variable: document_id
   - Initial value: 21cb377c-405d-4301-a666-23317f4332d1
5. Send
```

### Step 4: Update Document Status
```
1. New Request: "Update Document Status"
2. Method: PATCH
3. URL: http://localhost:8000/api/documents/{{document_id}}/status
4. Headers:
   - Content-Type: application/json
5. Body → raw → JSON:
   {
       "status": "active",
       "reason": "Testing from Postman"
   }
6. Send
```

### Step 5: Verify Status Changed
```
1. Run "Get Document by ID" again
2. Check response → "status" field should be "active"
3. Check "metadata" → "status_change_history" for audit trail
```

### Step 6: Toggle Status (active → superseded)
```
1. Use same "Update Document Status" request
2. Change Body:
   {
       "status": "superseded",
       "reason": "Replaced by new version"
   }
3. Send
4. Verify in "Get Document by ID"
```

---

## 🧪 Complete Test Sequence

### Script: `test_document_demo.sh`
```bash
#!/bin/bash
BASE_URL="http://localhost:8000/api"

echo "1. Get Stats"
curl -s "$BASE_URL/documents/stats/summary" | python3 -m json.tool

echo -e "\n2. Get First Document"
DOC_ID=$(curl -s "$BASE_URL/documents?limit=1" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")
echo "Document ID: $DOC_ID"

echo -e "\n3. Get Specific Document"
curl -s "$BASE_URL/documents/$DOC_ID" | python3 -m json.tool

echo -e "\n4. Update Status to 'active'"
curl -s -X PATCH "$BASE_URL/documents/$DOC_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "active", "reason": "Testing"}' | python3 -m json.tool

echo -e "\n5. Verify Status Changed"
curl -s "$BASE_URL/documents/$DOC_ID" | python3 -c "import sys, json; doc=json.load(sys.stdin); print(f\"Status: {doc['status']}\")"

echo -e "\n6. Update Status to 'superseded'"
curl -s -X PATCH "$BASE_URL/documents/$DOC_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "superseded", "reason": "Replaced by new version"}' | python3 -m json.tool

echo -e "\n7. Final Verification"
curl -s "$BASE_URL/documents/$DOC_ID" | python3 -m json.tool
```

---

## 📋 Postman Environment Variables

Create environment "Local RAG":

```json
{
  "name": "Local RAG",
  "values": [
    {
      "key": "base_url",
      "value": "http://localhost:8000/api",
      "enabled": true
    },
    {
      "key": "document_id",
      "value": "21cb377c-405d-4301-a666-23317f4332d1",
      "enabled": true
    }
  ]
}
```

Then use in requests:
- URL: `{{base_url}}/documents/{{document_id}}`

---

## 🔍 Common Filters Examples

### Filter by Document Type
```http
GET /api/documents?document_type=law&limit=10
GET /api/documents?document_type=decree&limit=10
GET /api/documents?document_type=bidding&limit=10
```

### Filter by Status (After Updates)
```http
GET /api/documents?status=active&limit=20
GET /api/documents?status=superseded&limit=10
GET /api/documents?status=draft&limit=5
```

### Pagination Example
```http
# Page 1 (0-49)
GET /api/documents?limit=50&offset=0

# Page 2 (50-99)
GET /api/documents?limit=50&offset=50

# Page 3 (100-149)
GET /api/documents?limit=50&offset=100
```

### Combined Filters
```http
GET /api/documents?document_type=law&status=active&limit=10
GET /api/documents?dieu=29&document_type=law&status=active
```

---

## ⚠️ Error Handling

### Document Not Found (404)
```json
{
    "detail": "Document not found"
}
```

### Invalid Status (422)
```json
{
    "detail": [
        {
            "type": "value_error",
            "loc": ["body", "status"],
            "msg": "Invalid status. Must be one of: draft, active, superseded, archived"
        }
    ]
}
```

---

## 🎯 Quick Demo Checklist

- [ ] Get statistics → See 4708 documents
- [ ] List first document → Copy ID
- [ ] Get document by ID → Verify details
- [ ] Update status to "active" → Check success response
- [ ] Get document again → Verify status changed
- [ ] Update status to "superseded" → Toggle status
- [ ] Check status_change_history in metadata → See audit trail

---

## 📊 Expected Results

**Statistics:**
- Total: 4708 documents
- Types: bidding (2831), law (1154), decree (595), circular (123), decision (5)
- Current status: null (chưa set)

**After Status Updates:**
- First update: null → active
- Second update: active → superseded
- Metadata contains full history với timestamps

---

**Created:** 2025-11-14  
**Last Updated:** 2025-11-14  
**Server:** http://localhost:8000
