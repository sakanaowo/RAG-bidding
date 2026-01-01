#!/bin/bash
# Test script for Documents API endpoints
# Usage: ./test_documents_api.sh

set -e  # Exit on error

BASE_URL="http://localhost:8000/api"
echo "=========================================="
echo "  TESTING DOCUMENTS API ENDPOINTS"
echo "  Base URL: $BASE_URL"
echo "=========================================="
echo ""

# Check if server is running
echo "🔍 Checking server health..."
if curl -s "$BASE_URL/../health" > /dev/null; then
    echo "✅ Server is running"
else
    echo "❌ Server is not running. Start with: ./start_server.sh"
    exit 1
fi
echo ""

# Test 1: Get document statistics
echo "=========================================="
echo "TEST 1: Document Statistics"
echo "=========================================="
echo "📊 GET /api/documents/stats/summary"
echo ""
curl -s "$BASE_URL/documents/stats/summary" | python -m json.tool
echo ""
echo ""

# Test 2: List first 10 documents
echo "=========================================="
echo "TEST 2: List Documents (First 10)"
echo "=========================================="
echo "📄 GET /api/documents?limit=10"
echo ""
curl -s "$BASE_URL/documents?limit=10" | python -m json.tool | head -100
echo ""
echo "... (truncated)"
echo ""

# Test 3: Filter by document type
echo "=========================================="
echo "TEST 3: Filter by Document Type = 'Luật'"
echo "=========================================="
echo "📄 GET /api/documents?document_type=Luật&limit=5"
echo ""
curl -s "$BASE_URL/documents?document_type=Luật&limit=5" | python -m json.tool
echo ""
echo ""

# Test 4: Filter by status
echo "=========================================="
echo "TEST 4: Filter by Status = 'active'"
echo "=========================================="
echo "📄 GET /api/documents?status=active&limit=5"
echo ""
curl -s "$BASE_URL/documents?status=active&limit=5" | python -m json.tool
echo ""
echo ""

# Test 5: Pagination
echo "=========================================="
echo "TEST 5: Pagination (Offset=10, Limit=5)"
echo "=========================================="
echo "📄 GET /api/documents?offset=10&limit=5"
echo ""
curl -s "$BASE_URL/documents?offset=10&limit=5" | python -m json.tool
echo ""
echo ""

# Test 6: Get specific document
echo "=========================================="
echo "TEST 6: Get Specific Document"
echo "=========================================="
echo "📄 First, get a document ID..."
DOC_ID=$(curl -s "$BASE_URL/documents?limit=1" | python -c "import sys, json; print(json.load(sys.stdin)[0]['id'])")
echo "   Document ID: $DOC_ID"
echo ""
echo "📄 GET /api/documents/$DOC_ID"
echo ""
curl -s "$BASE_URL/documents/$DOC_ID" | python -m json.tool
echo ""
echo ""

# Test 7: Get document by document_id (from metadata)
echo "=========================================="
echo "TEST 7: Get by Metadata document_id"
echo "=========================================="
echo "📄 First, get a document_id..."
METADATA_DOC_ID=$(curl -s "$BASE_URL/documents?limit=1" | python -c "import sys, json; print(json.load(sys.stdin)[0]['document_id'])")
echo "   Metadata document_id: $METADATA_DOC_ID"
echo ""
echo "📄 GET /api/documents/$METADATA_DOC_ID"
echo ""
curl -s "$BASE_URL/documents/$METADATA_DOC_ID" | python -m json.tool | head -50
echo ""
echo "... (truncated)"
echo ""

# Test 8: Complex query - Luật documents with pagination
echo "=========================================="
echo "TEST 8: Complex Query"
echo "=========================================="
echo "📄 GET /api/documents?document_type=Luật&status=active&limit=3&offset=0"
echo ""
curl -s "$BASE_URL/documents?document_type=Luật&status=active&limit=3&offset=0" | python -m json.tool
echo ""
echo ""

# Test 9: Search by dieu (article number)
echo "=========================================="
echo "TEST 9: Count Documents by Type"
echo "=========================================="
echo "📊 Counting documents for each type..."
echo ""
curl -s "$BASE_URL/documents/stats/summary" | python -c "
import sys, json
data = json.load(sys.stdin)
by_type = data.get('by_type', {})
print('Document Types:')
for doc_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
    print(f'  - {doc_type}: {count} documents')
print(f'\nTotal: {data.get(\"total_documents\", 0)} documents')
"
echo ""

echo "=========================================="
echo "✅ ALL TESTS COMPLETED"
echo "=========================================="
echo ""
echo "💡 Tips:"
echo "   - View all endpoints: curl http://localhost:8000/"
echo "   - API docs: http://localhost:8000/docs"
echo "   - Feature status: curl http://localhost:8000/features"
echo ""
