#!/bin/bash
# Complete Document API Demo Script

BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "  DOCUMENT API DEMO"
echo "  Testing all document endpoints"
echo "=========================================="

# Check server health
echo -e "\n🔍 Step 0: Check Server Health"
HEALTH=$(curl -s "$BASE_URL/../health")
if echo "$HEALTH" | grep -q '"db":true'; then
    echo "✅ Server is running and DB connected"
else
    echo "❌ Server not running or DB error"
    exit 1
fi

# 1. Get Statistics
echo -e "\n=========================================="
echo "📊 Step 1: Get Document Statistics"
echo "=========================================="
curl -s "$BASE_URL/documents/stats/summary" | python3 -m json.tool

# 2. List first document and extract ID
echo -e "\n=========================================="
echo "📄 Step 2: Get First Document"
echo "=========================================="
FIRST_DOC=$(curl -s "$BASE_URL/documents?limit=1")
echo "$FIRST_DOC" | python3 -m json.tool

DOC_ID=$(echo "$FIRST_DOC" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null)

if [ -z "$DOC_ID" ]; then
    echo "❌ Failed to extract document ID"
    exit 1
fi

echo -e "\n📌 Extracted Document ID: $DOC_ID"

# 3. Get specific document
echo -e "\n=========================================="
echo "🔍 Step 3: Get Document by ID"
echo "=========================================="
curl -s "$BASE_URL/documents/$DOC_ID" | python3 -m json.tool

# 4. Update status to 'active'
echo -e "\n=========================================="
echo "✏️  Step 4: Update Status → 'active'"
echo "=========================================="
UPDATE1=$(curl -s -X PATCH "$BASE_URL/documents/$DOC_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "active", "reason": "Demo: Setting document to active status"}')

echo "$UPDATE1" | python3 -m json.tool

# Check if successful
if echo "$UPDATE1" | grep -q '"success":true'; then
    echo "✅ Status updated successfully"
else
    echo "❌ Status update failed"
fi

# 5. Verify status changed
echo -e "\n=========================================="
echo "✅ Step 5: Verify Status Changed to 'active'"
echo "=========================================="
DOC_AFTER_1=$(curl -s "$BASE_URL/documents/$DOC_ID")
CURRENT_STATUS=$(echo "$DOC_AFTER_1" | python3 -c "import sys, json; doc=json.load(sys.stdin); print(doc.get('status', 'null'))" 2>/dev/null)

echo "Current Status: $CURRENT_STATUS"

if [ "$CURRENT_STATUS" = "active" ]; then
    echo "✅ Status confirmed: active"
else
    echo "⚠️  Status not updated correctly"
fi

# 6. Update status to 'superseded'
echo -e "\n=========================================="
echo "✏️  Step 6: Toggle Status → 'superseded'"
echo "=========================================="
UPDATE2=$(curl -s -X PATCH "$BASE_URL/documents/$DOC_ID/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "superseded", "reason": "Demo: Document replaced by newer version"}')

echo "$UPDATE2" | python3 -m json.tool

# 7. Final verification
echo -e "\n=========================================="
echo "✅ Step 7: Final Verification"
echo "=========================================="
DOC_FINAL=$(curl -s "$BASE_URL/documents/$DOC_ID")

# Extract status and history
FINAL_STATUS=$(echo "$DOC_FINAL" | python3 -c "import sys, json; doc=json.load(sys.stdin); print(doc.get('status', 'null'))" 2>/dev/null)

echo "Final Status: $FINAL_STATUS"

# Show full document with history
echo -e "\nFull Document Details:"
echo "$DOC_FINAL" | python3 -m json.tool

# 8. Test filtering by status
echo -e "\n=========================================="
echo "🔍 Step 8: Filter Documents by Status"
echo "=========================================="
echo "Active documents:"
curl -s "$BASE_URL/documents?status=active&limit=5" | python3 -c "import sys, json; docs=json.load(sys.stdin); print(f'Found {len(docs)} active documents')"

echo -e "\nSuperseded documents:"
curl -s "$BASE_URL/documents?status=superseded&limit=5" | python3 -c "import sys, json; docs=json.load(sys.stdin); print(f'Found {len(docs)} superseded documents')"

# Summary
echo -e "\n=========================================="
echo "  📋 DEMO SUMMARY"
echo "=========================================="
echo ""
echo "✅ Tested Endpoints:"
echo "  - GET /api/documents/stats/summary"
echo "  - GET /api/documents?limit=N"
echo "  - GET /api/documents/{id}"
echo "  - PATCH /api/documents/{id}/status"
echo ""
echo "✅ Status Updates:"
echo "  - null → active → superseded"
echo ""
echo "📌 Document ID Used: $DOC_ID"
echo "📌 Final Status: $FINAL_STATUS"
echo ""
echo "=========================================="
