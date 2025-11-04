"""
Test BGEReranker với BAAI/bge-reranker-v2-m3
"""

import sys

sys.path.insert(0, "/home/sakana/Code/RAG-bidding")

from langchain_core.documents import Document
from src.retrieval.ranking import BGEReranker

print("🧪 Testing BGEReranker (BAAI/bge-reranker-v2-m3)")
print("=" * 70)

# Initialize reranker
print("\n1️⃣ Initializing BGEReranker...")
reranker = BGEReranker(device="cpu")

# Sample query về bảo đảm dự thầu
query = "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023"

# Sample documents (giả lập từ vector search)
docs = [
    Document(
        page_content="Điều 14. Bảo đảm dự thầu\n1. Thời gian hiệu lực bảo đảm dự thầu được quy định trong hồ sơ mời thầu, tối thiểu là 30 ngày kể từ ngày hết hạn nộp hồ sơ dự thầu.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 14"},
    ),
    Document(
        page_content="Điều 68. Bảo đảm thực hiện hợp đồng\nThời hạn bảo đảm thực hiện hợp đồng được quy định trong hợp đồng, thường từ ngày ký hợp đồng đến khi hoàn thành nghĩa vụ.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 68"},
    ),
    Document(
        page_content="Điều 10. Ưu đãi nhà thầu trong nước\nNhà thầu trong nước được hưởng ưu đãi về giá trong đánh giá, ưu tiên xem xét trong trường hợp điểm kỹ thuật bằng nhau.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 10"},
    ),
    Document(
        page_content="Điều 25. Thời điểm có hiệu lực của hợp đồng\nHợp đồng có hiệu lực kể từ ngày được ký kết hoặc theo thỏa thuận của các bên trong hợp đồng.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 25"},
    ),
]

print(f"\n2️⃣ Testing rerank()...")
print(f"   📝 Query: {query}")
print(f"   📚 Documents to rerank: {len(docs)}")

# Rerank
results = reranker.rerank(query, docs, top_k=3)

print(f"\n3️⃣ Results:")
print(f"   🏆 Top 3 Results:")
print("-" * 70)
for i, (doc, score) in enumerate(results):
    article = doc.metadata.get("article", "Unknown")
    preview = doc.page_content[:100].replace("\n", " ")
    print(f"\n[{i+1}] Score: {score:.4f}")
    print(f"    Article: {article}")
    print(f"    Preview: {preview}...")

# Verify format
print("\n4️⃣ Verification:")
assert len(results) == 3, f"Expected 3 results, got {len(results)}"
assert all(isinstance(r, tuple) for r in results), "Results should be tuples"
assert all(len(r) == 2 for r in results), "Each result should be (doc, score)"
print("   ✅ Format correct: List[(Document, float)]")

# Check scores descending
scores = [score for _, score in results]
assert scores[0] >= scores[1] >= scores[2], "Scores should be descending"
print("   ✅ Scores are descending")

# Check correct ranking
top_article = results[0][0].metadata.get("article")
print(f"   🎯 Top ranked: {top_article}")
if "Điều 14" in top_article:
    print("   ✅ CORRECT! Điều 14 về bảo đảm dự thầu ranked #1")
else:
    print(f"   ⚠️  Unexpected: {top_article} ranked #1 instead of Điều 14")

# Test edge cases
print("\n5️⃣ Testing edge cases...")

# Empty docs
empty_results = reranker.rerank("test", [], top_k=5)
assert empty_results == [], "Empty docs should return empty list"
print("   ✅ Empty docs handled correctly")

# Single doc
single_results = reranker.rerank("test", docs[:1], top_k=5)
assert len(single_results) == 1, "Single doc should return 1 result"
print("   ✅ Single doc handled correctly")

# top_k limit
top2_results = reranker.rerank(query, docs, top_k=2)
assert len(top2_results) == 2, f"top_k=2 should return 2 results"
print("   ✅ top_k limit works correctly")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED!")
print("✅ BGEReranker is working correctly with BAAI/bge-reranker-v2-m3")
print("=" * 70)
