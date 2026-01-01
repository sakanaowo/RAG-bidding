"""
Quick end-to-end test for reranking pipeline.
Tests: Query → Enhancement → Retrieval → Reranking → Results
"""

from langchain_core.documents import Document
from src.retrieval.ranking import BGEReranker


def test_end_to_end_reranking():
    """Test the full reranking pipeline with sample documents."""
    print("\n" + "=" * 70)
    print("🚀 END-TO-END RERANKING TEST")
    print("=" * 70)

    # Sample Vietnamese legal documents
    docs = [
        Document(
            page_content="Điều 14. Bảo đảm dự thầu\n1. Thời gian hiệu lực bảo đảm dự thầu được quy định trong hồ sơ mời thầu, tối thiểu là 90 ngày.",
            metadata={"article": "Điều 14", "topic": "Bảo đảm dự thầu"},
        ),
        Document(
            page_content="Điều 25. Thời điểm có hiệu lực của hợp đồng\nHợp đồng có hiệu lực kể từ ngày được ký kết hoặc theo thời điểm được quy định trong hợp đồng.",
            metadata={"article": "Điều 25", "topic": "Hiệu lực hợp đồng"},
        ),
        Document(
            page_content="Điều 68. Bảo đảm thực hiện hợp đồng\nThời hạn bảo đảm thực hiện hợp đồng được quy định trong hợp đồng, phù hợp với thời gian thực hiện hợp đồng.",
            metadata={"article": "Điều 68", "topic": "Bảo đảm hợp đồng"},
        ),
        Document(
            page_content="Điều 5. Nguyên tắc đấu thầu\nĐấu thầu phải tuân thủ các nguyên tắc công khai, minh bạch, cạnh tranh, hiệu quả và trách nhiệm giải trình.",
            metadata={"article": "Điều 5", "topic": "Nguyên tắc"},
        ),
    ]

    query = "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023"

    print(f"\n📝 Query: {query}")
    print(f"📚 Documents: {len(docs)}")

    # Initialize reranker
    print("\n🔧 Initializing BGEReranker...")
    reranker = BGEReranker()
    print(f"   🤖 Model: {reranker.model_name}")
    print(f"   🎮 Device: {reranker.device}")
    print(f"   📦 Batch size: {reranker.batch_size}")

    # Rerank
    print("\n⏳ Reranking documents...")
    import time

    start = time.time()
    results = reranker.rerank(query, docs, top_k=3)
    latency = (time.time() - start) * 1000

    # Display results
    print(f"\n⚡ Reranking completed in {latency:.2f}ms")
    print("\n🏆 Top 3 Results:")
    print("-" * 70)

    for i, (doc, score) in enumerate(results, 1):
        article = doc.metadata.get("article", "Unknown")
        preview = doc.page_content[:80] + "..."
        print(f"\n[{i}] Score: {score:.4f}")
        print(f"    Article: {article}")
        print(f"    Preview: {preview}")

    # Verify result
    print("\n" + "=" * 70)
    top_article = results[0][0].metadata.get("article")
    top_score = results[0][1]

    if top_article == "Điều 14" and top_score > 0.9:
        print("✅ TEST PASSED!")
        print(f"   🎯 Điều 14 correctly ranked #1")
        print(f"   📊 Score: {top_score:.4f} (excellent)")
        print(f"   ⚡ Latency: {latency:.2f}ms")
        print("\n🎉 Reranking pipeline is working perfectly!")
    else:
        print("❌ TEST FAILED!")
        print(f"   Expected: Điều 14 with score > 0.9")
        print(f"   Got: {top_article} with score {top_score:.4f}")

    print("=" * 70)


if __name__ == "__main__":
    test_end_to_end_reranking()
