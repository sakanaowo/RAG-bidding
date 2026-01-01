#!/usr/bin/env python3
"""
Test script: Document status filtering in retrieval

Scenario:
1. Toggle document status to 'expired'
2. Ask question related to that document
3. Verify document is NOT retrieved (filter_status='active' by default)
4. Restore status to 'active'
5. Ask same question again
6. Verify document IS retrieved now

Usage:
    python scripts/test/test_status_filter.py
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def toggle_document_status(document_id: str, new_status: str) -> Dict[str, Any]:
    """Toggle document status via API."""
    url = f"{BASE_URL}/api/documents/{document_id}/status"
    params = {"new_status": new_status}

    print(f"📝 Toggling document '{document_id}' to status='{new_status}'...")
    response = requests.patch(url, params=params)
    response.raise_for_status()

    result = response.json()
    print(f"✅ Status changed: {result['old_status']} → {result['new_status']}")
    print(f"   Synced to {result['chunks_updated']} chunks in vector DB")
    return result


def ask_question(question: str, mode: str = "fast") -> Dict[str, Any]:
    """Ask question via /ask endpoint."""
    url = f"{BASE_URL}/ask"
    payload = {"question": question, "mode": mode, "reranker": "bge"}

    print(f"💬 Question: {question}")
    print(f"   Mode: {mode}")

    response = requests.post(url, json=payload)
    response.raise_for_status()

    result = response.json()
    print(f"⏱️  Processing time: {result.get('processing_time_ms', 0)}ms")
    print(f"📚 Sources retrieved: {len(result.get('sources', []))}")

    return result


def check_if_document_in_sources(sources: list, document_id: str) -> bool:
    """Check if document_id appears in any source."""
    for source in sources:
        if document_id in source:
            return True
    return False


def list_documents(status: str = None) -> Dict[str, Any]:
    """List documents with optional status filter."""
    url = f"{BASE_URL}/api/documents"
    params = {}
    if status:
        params["status"] = status

    response = requests.get(url, params=params)
    response.raise_for_status()

    return response.json()


def main():
    """Run test scenario."""
    print_section("🧪 TEST: Document Status Filtering in Retrieval")

    # Test configuration
    TEST_DOCUMENT_ID = "6-Mau-so-6C-E-TVCN-tu-van-ca-nhan"
    TEST_QUESTION = "Mẫu số 6C là gì? Dùng để làm gì?"

    print(f"Target document: {TEST_DOCUMENT_ID}")
    print(f"Test question: {TEST_QUESTION}")

    try:
        # Step 1: Check current document status
        print_section("STEP 1: Check Current Document Status")
        docs = list_documents()
        target_doc = next(
            (d for d in docs if d.get("document_id") == TEST_DOCUMENT_ID), None
        )

        if not target_doc:
            print(f"❌ Document '{TEST_DOCUMENT_ID}' not found in database")
            return

        original_status = target_doc.get("status", "active")
        print(f"📄 Document found")
        print(f"   Name: {target_doc.get('document_name')}")
        print(f"   Type: {target_doc.get('document_type')}")
        print(f"   Status: {original_status}")
        print(f"   Total chunks: {target_doc.get('total_chunks')}")

        # Step 2: Set status to 'expired'
        print_section("STEP 2: Toggle Status to 'expired'")
        toggle_document_status(TEST_DOCUMENT_ID, "expired")

        time.sleep(1)  # Wait for sync

        # Step 3: Ask question (should NOT retrieve expired document)
        print_section("STEP 3: Query with filter_status='active' (Default)")
        result_expired = ask_question(TEST_QUESTION, mode="fast")

        doc_found_when_expired = check_if_document_in_sources(
            result_expired.get("sources", []), TEST_DOCUMENT_ID
        )

        print(f"\n🔍 Result Analysis:")
        print(
            f"   Document retrieved: {'YES ❌' if doc_found_when_expired else 'NO ✅'}"
        )
        print(f"   Answer: {result_expired.get('answer', '')[:200]}...")

        if doc_found_when_expired:
            print(f"\n⚠️  WARNING: Expired document was retrieved (filter not working!)")
        else:
            print(f"\n✅ PASS: Expired document correctly filtered out")

        # Step 4: Restore status to original
        print_section("STEP 4: Restore Status to 'active'")
        toggle_document_status(TEST_DOCUMENT_ID, "active")

        time.sleep(1)  # Wait for sync

        # Step 5: Ask same question (should retrieve active document)
        print_section("STEP 5: Query Again with Status='active'")
        result_active = ask_question(TEST_QUESTION, mode="fast")

        doc_found_when_active = check_if_document_in_sources(
            result_active.get("sources", []), TEST_DOCUMENT_ID
        )

        print(f"\n🔍 Result Analysis:")
        print(
            f"   Document retrieved: {'YES ✅' if doc_found_when_active else 'NO ❌'}"
        )
        print(f"   Answer: {result_active.get('answer', '')[:200]}...")

        if doc_found_when_active:
            print(f"\n✅ PASS: Active document correctly retrieved")
        else:
            print(f"\n⚠️  WARNING: Active document was NOT retrieved (unexpected!)")

        # Final summary
        print_section("📊 TEST SUMMARY")

        print(f"Test Scenario: Status-based retrieval filtering")
        print(f"Document ID: {TEST_DOCUMENT_ID}")
        print(f"Question: {TEST_QUESTION}\n")

        print(f"Results:")
        print(
            f"  1. Expired document filtered out: {'✅ PASS' if not doc_found_when_expired else '❌ FAIL'}"
        )
        print(
            f"  2. Active document retrieved: {'✅ PASS' if doc_found_when_active else '❌ FAIL'}"
        )

        overall_pass = (not doc_found_when_expired) and doc_found_when_active

        print(f"\n{'='*80}")
        if overall_pass:
            print(f"  ✅ ALL TESTS PASSED")
            print(f"  Status filtering works correctly!")
        else:
            print(f"  ❌ SOME TESTS FAILED")
            print(f"  Check retrieval filter logic")
        print(f"{'='*80}\n")

        return overall_pass

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
