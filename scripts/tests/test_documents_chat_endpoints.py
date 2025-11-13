"""
Test script for new Documents & Chat API endpoints

Tests:
1. GET /api/documents - List all documents
2. GET /api/documents/{id} - Get specific document
3. GET /api/documents/stats/summary - Get statistics
4. POST /api/chat/sessions - Create chat session
5. POST /api/chat/sessions/{id}/messages - Send message
6. GET /api/chat/sessions/{id}/history - Get history
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api"


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def print_response(response: requests.Response, show_data: bool = True):
    """Print formatted API response."""
    print(f"Status: {response.status_code}")
    print(f"Time: {response.elapsed.total_seconds():.2f}s")

    if show_data:
        try:
            data = response.json()
            print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"Response: {response.text}")
    print()


def test_list_documents():
    """Test: GET /api/documents - List all documents."""
    print_section("TEST 1: List Documents")

    # Test basic listing
    print("📄 Fetching first 5 documents...")
    response = requests.get(f"{BASE_URL}/documents", params={"limit": 5})
    print_response(response)

    # Test filtering by document type
    print("📄 Filtering by document type = 'Luật'...")
    response = requests.get(
        f"{BASE_URL}/documents", params={"limit": 3, "document_type": "Luật"}
    )
    print_response(response)

    # Test filtering by status
    print("📄 Filtering by status = 'active'...")
    response = requests.get(
        f"{BASE_URL}/documents", params={"limit": 3, "status": "active"}
    )
    print_response(response)

    # Test pagination
    print("📄 Testing pagination (offset=5)...")
    response = requests.get(f"{BASE_URL}/documents", params={"limit": 3, "offset": 5})
    print_response(response)


def test_get_document():
    """Test: GET /api/documents/{id} - Get specific document."""
    print_section("TEST 2: Get Specific Document")

    # First, get a document ID from list
    print("📄 Getting document ID from list...")
    response = requests.get(f"{BASE_URL}/documents", params={"limit": 1})

    if response.status_code == 200:
        docs = response.json()
        if docs:
            doc_id = docs[0]["id"]
            document_id = docs[0]["document_id"]

            # Test get by UUID
            print(f"📄 Fetching document by UUID: {doc_id}...")
            response = requests.get(f"{BASE_URL}/documents/{doc_id}")
            print_response(response)

            # Test get by document_id
            print(f"📄 Fetching document by document_id: {document_id}...")
            response = requests.get(f"{BASE_URL}/documents/{document_id}")
            print_response(response)
        else:
            print("❌ No documents found in database")
    else:
        print(f"❌ Failed to list documents: {response.status_code}")


def test_document_stats():
    """Test: GET /api/documents/stats/summary - Get statistics."""
    print_section("TEST 3: Document Statistics")

    print("📊 Fetching document statistics...")
    response = requests.get(f"{BASE_URL}/documents/stats/summary")
    print_response(response)


def test_chat_session_flow():
    """Test: Complete chat session flow."""
    print_section("TEST 4: Chat Session Flow")

    # 1. Create session
    print("💬 Creating new chat session...")
    response = requests.post(
        f"{BASE_URL}/chat/sessions", params={"user_id": "test_user_123"}
    )
    print_response(response)

    if response.status_code != 200:
        print("❌ Failed to create session")
        return

    session_id = response.json()["session_id"]
    print(f"✅ Session created: {session_id}\n")

    # 2. Send first message
    print("💬 Sending first message...")
    message_1 = {
        "message": "Điều kiện tham gia đấu thầu là gì?",
        "metadata": {"test": True},
    }
    response = requests.post(
        f"{BASE_URL}/chat/sessions/{session_id}/messages", json=message_1
    )
    print_response(response, show_data=False)  # Don't show full answer

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response received ({data.get('processing_time_ms', 0)}ms)")
        print(f"   Answer preview: {data['assistant_response'][:200]}...")
        print(f"   Sources: {len(data.get('sources', []))} documents")
    else:
        print(f"❌ Failed to send message: {response.status_code}")

    # Wait a bit
    time.sleep(1)

    # 3. Send follow-up message
    print("\n💬 Sending follow-up message...")
    message_2 = {
        "message": "Giải thích rõ hơn về điều kiện tài chính",
        "metadata": {"test": True, "follow_up": True},
    }
    response = requests.post(
        f"{BASE_URL}/chat/sessions/{session_id}/messages", json=message_2
    )
    print_response(response, show_data=False)

    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response received ({data.get('processing_time_ms', 0)}ms)")
        print(f"   Answer preview: {data['assistant_response'][:200]}...")

    # 4. Get conversation history
    print("\n💬 Fetching conversation history...")
    response = requests.get(f"{BASE_URL}/chat/sessions/{session_id}/history")
    print_response(response)

    # 5. List active sessions
    print("💬 Listing active sessions...")
    response = requests.get(f"{BASE_URL}/chat/sessions")
    print_response(response)

    # 6. Delete session
    print(f"💬 Deleting session {session_id}...")
    response = requests.delete(f"{BASE_URL}/chat/sessions/{session_id}")
    print_response(response)


def test_error_handling():
    """Test: Error handling for invalid requests."""
    print_section("TEST 5: Error Handling")

    # Test invalid document ID
    print("❌ Testing invalid document ID...")
    response = requests.get(f"{BASE_URL}/documents/invalid-uuid-12345")
    print_response(response)

    # Test invalid session ID
    print("❌ Testing invalid session ID...")
    response = requests.get(f"{BASE_URL}/chat/sessions/invalid-session/history")
    print_response(response)

    # Test send message to non-existent session
    print("❌ Testing message to non-existent session...")
    response = requests.post(
        f"{BASE_URL}/chat/sessions/non-existent/messages", json={"message": "test"}
    )
    print_response(response)


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  DOCUMENTS & CHAT API ENDPOINT TESTS")
    print("  Base URL:", BASE_URL)
    print("=" * 80)

    try:
        # Test documents endpoints
        test_list_documents()
        test_get_document()
        test_document_stats()

        # Test chat endpoints
        test_chat_session_flow()

        # Test error handling
        test_error_handling()

        print_section("✅ ALL TESTS COMPLETED")

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("   Make sure server is running on http://localhost:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
