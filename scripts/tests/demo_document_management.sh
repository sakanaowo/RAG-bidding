#!/bin/bash
# Demo Document Management API - Document-level operations

BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "  DOCUMENT MANAGEMENT API DEMO"
echo "  Document-level operations (not chunks)"
echo "=========================================="

# Check server
echo -e "\n🔍 Step 0: Check Server"
if ! curl -s "$BASE_URL/../health" | grep -q '"db":true'; then
    echo "❌ Server not running or DB error"
    exit 1
fi
echo "✅ Server running"

# 1. Get document catalog (list of unique documents)
echo -e "\n=========================================="
echo "📚 Step 1: Get Document Catalog"
echo "=========================================="
echo "Endpoint: GET /documents/catalog"
echo ""

CATALOG=$(curl -s "$BASE_URL/documents/catalog?limit=5")
echo "$CATALOG" | python3 -m json.tool

# Extract first document_id
DOC_ID=$(echo "$CATALOG" | python3 -c "import sys, json; docs=json.load(sys.stdin); print(docs[0]['document_id'] if docs else '')" 2>/dev/null)

if [ -z "$DOC_ID" ]; then
    echo "❌ No documents found in catalog"
    exit 1
fi

echo -e "\n📌 Selected Document ID: $DOC_ID"

# 2. Get full document details
echo -e "\n=========================================="
echo "📄 Step 2: Get Full Document Details"
echo "=========================================="
echo "Endpoint: GET /documents/catalog/{document_id}"
echo ""

DOC_DETAIL=$(curl -s "$BASE_URL/documents/catalog/$DOC_ID")

# Pretty print summary
echo "$DOC_DETAIL" | python3 << 'EOF'
import sys, json
doc = json.load(sys.stdin)

print(f"Document ID: {doc['document_id']}")
print(f"Title: {doc['title']}")
print(f"Type: {doc['document_type']}")
print(f"Total Chunks: {doc['total_chunks']}")
print(f"Current Status: {doc['status']}")
print(f"\nStatus History ({len(doc['status_history'])} changes):")
for i, change in enumerate(doc['status_history'][-3:], 1):  # Last 3 changes
    print(f"  {i}. {change['from_status']} → {change['to_status']}")
    print(f"     Reason: {change['reason']}")
    print(f"     Time: {change['timestamp']}")

print(f"\nChunks Preview (showing first 2 of {len(doc['chunks'])}):")
for i, chunk in enumerate(doc['chunks'][:2], 1):
    content = chunk['content'][:100] + "..." if len(chunk['content']) > 100 else chunk['content']
    print(f"  Chunk {chunk['chunk_index']}: {content}")
EOF

# 3. Get document statistics
echo -e "\n=========================================="
echo "📊 Step 3: Get Document Statistics"
echo "=========================================="
echo "Endpoint: GET /documents/catalog/{document_id}/stats"
echo ""

curl -s "$BASE_URL/documents/catalog/$DOC_ID/stats" | python3 -m json.tool

# 4. Update document status
echo -e "\n=========================================="
echo "✏️  Step 4: Update Document Status"
echo "=========================================="
echo "Endpoint: PATCH /documents/catalog/{document_id}/status"
echo ""

# Update to 'active'
echo "Updating status to 'active'..."
UPDATE_RESULT=$(curl -s -X PATCH "$BASE_URL/documents/catalog/$DOC_ID/status" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active",
    "reason": "Demo: Testing document-level status update from catalog API"
  }')

echo "$UPDATE_RESULT" | python3 -m json.tool

# Check if successful
if echo "$UPDATE_RESULT" | grep -q '"success":true'; then
    echo "✅ Status updated successfully"
    
    CHUNKS_UPDATED=$(echo "$UPDATE_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin)['chunks_updated'])" 2>/dev/null)
    echo "📌 Updated $CHUNKS_UPDATED chunks"
else
    echo "❌ Status update failed"
fi

# 5. Verify status changed
echo -e "\n=========================================="
echo "✅ Step 5: Verify Status Changed"
echo "=========================================="
sleep 1  # Wait for DB update

UPDATED_DOC=$(curl -s "$BASE_URL/documents/catalog/$DOC_ID")

echo "$UPDATED_DOC" | python3 << 'EOF'
import sys, json
doc = json.load(sys.stdin)

print(f"Document ID: {doc['document_id']}")
print(f"Current Status: {doc['status']}")
print(f"\nLatest Status Changes:")
for i, change in enumerate(doc['status_history'][-2:], 1):  # Last 2 changes
    print(f"  {i}. {change['from_status']} → {change['to_status']}")
    print(f"     Reason: {change['reason']}")
    print(f"     Time: {change['timestamp'][:19]}")
EOF

# 6. Filter by document type
echo -e "\n=========================================="
echo "🔍 Step 6: Filter Catalog by Type"
echo "=========================================="
echo "Endpoint: GET /documents/catalog?document_type=bidding"
echo ""

BIDDING_DOCS=$(curl -s "$BASE_URL/documents/catalog?document_type=bidding&limit=3")

echo "$BIDDING_DOCS" | python3 << 'EOF'
import sys, json
docs = json.load(sys.stdin)

print(f"Found {len(docs)} bidding documents:")
for i, doc in enumerate(docs, 1):
    print(f"\n{i}. {doc['title']}")
    print(f"   ID: {doc['document_id']}")
    print(f"   Chunks: {doc['total_chunks']}")
    print(f"   Status: {doc['status']}")
EOF

# 7. Toggle status again (active → superseded)
echo -e "\n=========================================="
echo "🔄 Step 7: Toggle Status (active → superseded)"
echo "=========================================="

curl -s -X PATCH "$BASE_URL/documents/catalog/$DOC_ID/status" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "superseded",
    "reason": "Demo: Document replaced by newer version"
  }' | python3 << 'EOF'
import sys, json
result = json.load(sys.stdin)

if result.get('success'):
    print(f"✅ Status changed: {result['old_status']} → {result['new_status']}")
    print(f"   Chunks updated: {result['chunks_updated']}")
    print(f"   Reason: {result['reason']}")
else:
    print("❌ Update failed")
EOF

# Summary
echo -e "\n=========================================="
echo "  📋 DEMO SUMMARY"
echo "=========================================="
echo ""
echo "✅ Tested Endpoints:"
echo "  - GET /api/documents/catalog (list unique documents)"
echo "  - GET /api/documents/catalog/{id} (full document with all chunks)"
echo "  - GET /api/documents/catalog/{id}/stats (statistics)"
echo "  - PATCH /api/documents/catalog/{id}/status (update status for ALL chunks)"
echo ""
echo "✅ Features Demonstrated:"
echo "  - Document-level operations (not chunk-level)"
echo "  - Title extraction from hierarchy"
echo "  - Status updates apply to ALL chunks"
echo "  - Status change history tracking"
echo "  - Document statistics aggregation"
echo ""
echo "📌 Document ID Used: $DOC_ID"
echo ""
echo "🎯 Key Differences from /documents endpoint:"
echo "  - /documents: Returns individual CHUNKS"
echo "  - /documents/catalog: Returns complete DOCUMENTS (grouped by document_id)"
echo "  - Status update affects ALL chunks in document"
echo "  - Includes title, total chunks, aggregated metadata"
echo ""
echo "=========================================="
