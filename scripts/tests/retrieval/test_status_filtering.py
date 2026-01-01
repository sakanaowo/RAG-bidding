"""
Test script to verify status filtering is working correctly.

This script will:
1. Query without filter (get all documents)
2. Query with filter_status="active" (only active documents)
3. Query with filter_status="expired" (only expired documents)
4. Compare results
"""

import sys

sys.path.append("/home/sakana/Code/RAG-bidding")

from src.retrieval.retrievers.base_vector_retriever import BaseVectorRetriever
from src.embedding.store.pgvector_store import vector_store


def test_status_filtering():
    """Test status filtering functionality."""

    test_query = "Quy trình đấu thầu rộng rãi quốc tế"

    print("=" * 80)
    print("🧪 TESTING STATUS FILTERING")
    print("=" * 80)
    print(f"\n📝 Test Query: '{test_query}'")
    print(f"📊 Testing with k=10 documents\n")

    # Test 1: No filter (baseline)
    print("\n" + "=" * 80)
    print("TEST 1: NO FILTER (All Documents)")
    print("=" * 80)

    retriever_no_filter = BaseVectorRetriever(k=10, filter_status=None)
    docs_all = retriever_no_filter._get_relevant_documents(test_query)

    print(f"✅ Retrieved: {len(docs_all)} documents")
    print("\n📄 Sample results:")

    status_counts = {"active": 0, "expired": 0, "no_status": 0}

    for i, doc in enumerate(docs_all[:10], 1):
        status = doc.metadata.get("status", "NO_STATUS")
        valid_until = doc.metadata.get("valid_until", "N/A")
        source = doc.metadata.get("source", "N/A")

        # Count statuses
        if status == "active":
            status_counts["active"] += 1
        elif status == "expired":
            status_counts["expired"] += 1
        else:
            status_counts["no_status"] += 1

        # Extract filename or URL
        if source == "thuvienphapluat.vn":
            url = doc.metadata.get("url", "N/A")
            filename = url.split("/")[-1][:60] if url != "N/A" else "N/A"
        else:
            filename = source.split("/")[-1] if source != "N/A" else "N/A"

        emoji = "✅" if status == "active" else "❌" if status == "expired" else "❓"
        print(
            f"{i}. {emoji} Status: {status:8} | Valid until: {valid_until} | {filename[:50]}"
        )

    print(f"\n📊 Status Distribution (No Filter):")
    print(f"   ✅ Active: {status_counts['active']}")
    print(f"   ❌ Expired: {status_counts['expired']}")
    print(f"   ❓ No Status: {status_counts['no_status']}")

    # Test 2: Filter active only
    print("\n" + "=" * 80)
    print("TEST 2: FILTER STATUS = 'active'")
    print("=" * 80)

    retriever_active = BaseVectorRetriever(k=10, filter_status="active")
    docs_active = retriever_active._get_relevant_documents(test_query)

    print(f"✅ Retrieved: {len(docs_active)} documents")
    print("\n📄 Sample results:")

    active_status_counts = {"active": 0, "expired": 0, "no_status": 0}

    for i, doc in enumerate(docs_active[:10], 1):
        status = doc.metadata.get("status", "NO_STATUS")
        valid_until = doc.metadata.get("valid_until", "N/A")
        source = doc.metadata.get("source", "N/A")

        # Count statuses
        if status == "active":
            active_status_counts["active"] += 1
        elif status == "expired":
            active_status_counts["expired"] += 1
        else:
            active_status_counts["no_status"] += 1

        # Extract filename or URL
        if source == "thuvienphapluat.vn":
            url = doc.metadata.get("url", "N/A")
            filename = url.split("/")[-1][:60] if url != "N/A" else "N/A"
        else:
            filename = source.split("/")[-1] if source != "N/A" else "N/A"

        emoji = "✅" if status == "active" else "❌" if status == "expired" else "❓"
        print(
            f"{i}. {emoji} Status: {status:8} | Valid until: {valid_until} | {filename[:50]}"
        )

    print(f"\n📊 Status Distribution (Active Filter):")
    print(f"   ✅ Active: {active_status_counts['active']}")
    print(f"   ❌ Expired: {active_status_counts['expired']}")
    print(f"   ❓ No Status: {active_status_counts['no_status']}")

    # Test 3: Filter expired only
    print("\n" + "=" * 80)
    print("TEST 3: FILTER STATUS = 'expired'")
    print("=" * 80)

    retriever_expired = BaseVectorRetriever(k=10, filter_status="expired")
    docs_expired = retriever_expired._get_relevant_documents(test_query)

    print(f"✅ Retrieved: {len(docs_expired)} documents")
    print("\n📄 Sample results:")

    expired_status_counts = {"active": 0, "expired": 0, "no_status": 0}

    for i, doc in enumerate(docs_expired[:10], 1):
        status = doc.metadata.get("status", "NO_STATUS")
        valid_until = doc.metadata.get("valid_until", "N/A")
        source = doc.metadata.get("source", "N/A")

        # Count statuses
        if status == "active":
            expired_status_counts["active"] += 1
        elif status == "expired":
            expired_status_counts["expired"] += 1
        else:
            expired_status_counts["no_status"] += 1

        # Extract filename or URL
        if source == "thuvienphapluat.vn":
            url = doc.metadata.get("url", "N/A")
            filename = url.split("/")[-1][:60] if url != "N/A" else "N/A"
        else:
            filename = source.split("/")[-1] if source != "N/A" else "N/A"

        emoji = "✅" if status == "active" else "❌" if status == "expired" else "❓"
        print(
            f"{i}. {emoji} Status: {status:8} | Valid until: {valid_until} | {filename[:50]}"
        )

    print(f"\n📊 Status Distribution (Expired Filter):")
    print(f"   ✅ Active: {expired_status_counts['active']}")
    print(f"   ❌ Expired: {expired_status_counts['expired']}")
    print(f"   ❓ No Status: {expired_status_counts['no_status']}")

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(
        f"\n1️⃣  No Filter:      {len(docs_all)} docs (Active: {status_counts['active']}, Expired: {status_counts['expired']})"
    )
    print(
        f"2️⃣  Active Filter:  {len(docs_active)} docs (Active: {active_status_counts['active']}, Expired: {active_status_counts['expired']})"
    )
    print(
        f"3️⃣  Expired Filter: {len(docs_expired)} docs (Active: {expired_status_counts['active']}, Expired: {expired_status_counts['expired']})"
    )

    # Validation
    print("\n" + "=" * 80)
    print("✅ VALIDATION")
    print("=" * 80)

    validation_passed = True

    # Check 1: Active filter should only return active docs
    if active_status_counts["expired"] > 0 or active_status_counts["no_status"] > 0:
        print("❌ FAILED: Active filter returned non-active documents!")
        validation_passed = False
    else:
        print("✅ PASSED: Active filter only returns active documents")

    # Check 2: Expired filter should only return expired docs
    if expired_status_counts["active"] > 0 or expired_status_counts["no_status"] > 0:
        print("❌ FAILED: Expired filter returned non-expired documents!")
        validation_passed = False
    else:
        print("✅ PASSED: Expired filter only returns expired documents")

    # Check 3: All docs should have status field
    if status_counts["no_status"] > 0:
        print(
            f"⚠️  WARNING: {status_counts['no_status']} documents without status field"
        )
    else:
        print("✅ PASSED: All documents have status field")

    print("\n" + "=" * 80)
    if validation_passed:
        print("🎉 ALL TESTS PASSED! Status filtering is working correctly.")
    else:
        print("❌ TESTS FAILED! Status filtering is NOT working correctly.")
    print("=" * 80)


if __name__ == "__main__":
    test_status_filtering()
