"""
Test API with status filtering enabled.

This script simulates API requests to verify:
1. Default behavior (filter_status="active")
2. Retrieval only returns active documents
3. Enhanced sources include status information
"""

import sys

sys.path.append("/home/sakana/Code/RAG-bidding")

from src.generation.chains.qa_chain import answer
from src.retrieval.retrievers import create_retriever


def test_api_with_filtering():
    """Test API with status filtering."""

    print("=" * 80)
    print("🧪 TESTING API WITH STATUS FILTERING")
    print("=" * 80)

    test_queries = [
        "Quy trình đấu thầu rộng rãi quốc tế",
        "Các hình thức lựa chọn nhà thầu",
        "Điều kiện để tham gia đấu thầu",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}: Query = '{query}'")
        print(f"{'=' * 80}")

        # Test with balanced mode (default filtering)
        result = answer(question=query, mode="balanced")

        # answer() returns formatted strings for sources; to verify filtering we
        # create the same retriever and fetch Document objects (with metadata)
        selected_mode = result.get("adaptive_retrieval", {}).get("mode", "balanced")
        print(f"\n📝 Query: {query}")
        print(f"🎯 Mode: {selected_mode}")
        print(f"⚡ Enhanced: {result.get('enhanced_features', [])}")
        print(f"📊 Answer produced, now checking underlying retriever results...\n")

        # Build retriever the same way the chain does (create_retriever defaults to filter_status="active")
        retriever = create_retriever(mode=selected_mode)
        docs = retriever._get_relevant_documents(query)

        print(f"✅ Retrieved (via retriever): {len(docs)} documents (inspect first 10)")

        # Check status distribution from real Document.metadata
        status_counts = {"active": 0, "expired": 0, "no_status": 0}
        print("\n📄 Source Status (from Document.metadata):")
        for j, doc in enumerate(docs[:10], 1):
            status = doc.metadata.get("status", "NO_STATUS")
            valid_until = doc.metadata.get("valid_until", "N/A")
            source = doc.metadata.get("source", "N/A")

            if status == "active":
                status_counts["active"] += 1
            elif status == "expired":
                status_counts["expired"] += 1
            else:
                status_counts["no_status"] += 1

            # Extract source name
            if source == "thuvienphapluat.vn":
                url = doc.metadata.get("url", "N/A")
                source_name = url.split("/")[-1][:50] if url != "N/A" else "N/A"
            else:
                source_name = source.split("/")[-1] if source != "N/A" else "N/A"

            emoji = (
                "✅" if status == "active" else "❌" if status == "expired" else "❓"
            )
            print(
                f"   {j}. {emoji} {status:8} | Valid: {valid_until} | {source_name[:45]}"
            )

        print(f"\n📊 Status Distribution (retriever):")
        print(f"   ✅ Active: {status_counts['active']}")
        print(f"   ❌ Expired: {status_counts['expired']}")
        print(f"   ❓ No Status: {status_counts['no_status']}")

        # Validation
        if status_counts["expired"] > 0:
            print(
                f"\n⚠️  WARNING: Found {status_counts['expired']} expired documents via retriever!"
            )
        else:
            print(f"\n✅ SUCCESS: All retrieved documents via retriever are ACTIVE")

        print(f"\n💬 Answer Preview (first 200 chars):")
        print(f"   {result.get('answer','')[:200]}...")

    print("\n" + "=" * 80)
    print("🎉 API TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_api_with_filtering()
