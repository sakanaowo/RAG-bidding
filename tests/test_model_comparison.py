"""
Test BGE Reranker (fine-tuned model) vs PhoBERT (not fine-tuned)
"""

import sys

sys.path.insert(0, "/home/sakana/Code/RAG-bidding")

from langchain_core.documents import Document
from src.retrieval.ranking import PhoBERTReranker

print("🧪 Comparing Fine-tuned vs Not Fine-tuned Models")
print("=" * 70)

# Sample query về bảo đảm dự thầu
query = "Quy định về thời gian hiệu lực bảo đảm dự thầu trong Luật Đấu thầu 2023"

# Sample documents
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
        page_content="Điều 10. Ưu đãi nhà thầu trong nước\nNhà thầu trong nước được hưởng ưu đãi về giá trong đánh giá.",
        metadata={"source": "Luật Đấu thầu 2023", "article": "Điều 10"},
    ),
]

print(f"\n📝 Query: {query}\n")

# Test 1: BGE Reranker (FINE-TUNED) ⭐
print("─" * 70)
print("1️⃣ Testing BAAI/bge-reranker-v2-m3 (FINE-TUNED for reranking)")
print("─" * 70)

reranker_bge = PhoBERTReranker(model_name="BAAI/bge-reranker-v2-m3", device="cpu")

results_bge = reranker_bge.rerank(query, docs, top_k=3)

print("\n🏆 Results:")
for i, (doc, score) in enumerate(results_bge):
    article = doc.metadata.get("article", "Unknown")
    print(f"[{i+1}] {article}: {score:.4f}")

print(f"\n✅ Top ranked: {results_bge[0][0].metadata.get('article')}")
print(f"✅ Score range: {results_bge[-1][1]:.4f} to {results_bge[0][1]:.4f}")
print(f"✅ Score difference: {results_bge[0][1] - results_bge[-1][1]:.4f}")

# Test 2: PhoBERT (NOT FINE-TUNED)
print("\n" + "─" * 70)
print("2️⃣ Testing vinai/phobert-base-v2 (NOT fine-tuned for reranking)")
print("─" * 70)

reranker_phobert = PhoBERTReranker(model_name="vinai/phobert-base-v2", device="cpu")

results_phobert = reranker_phobert.rerank(query, docs, top_k=3)

print("\n🏆 Results:")
for i, (doc, score) in enumerate(results_phobert):
    article = doc.metadata.get("article", "Unknown")
    print(f"[{i+1}] {article}: {score:.4f}")

print(f"\n⚠️  Top ranked: {results_phobert[0][0].metadata.get('article')}")
print(f"⚠️  Score range: {results_phobert[-1][1]:.4f} to {results_phobert[0][1]:.4f}")
print(f"⚠️  Score difference: {results_phobert[0][1] - results_phobert[-1][1]:.4f}")

# Comparison
print("\n" + "=" * 70)
print("📊 COMPARISON")
print("=" * 70)

print(f"\nBGE (fine-tuned):")
print(f"  - Top doc: {results_bge[0][0].metadata.get('article')}")
print(
    f"  - Score separation: {results_bge[0][1] - results_bge[-1][1]:.4f} (higher = better)"
)
print(f"  - Warnings: NONE ✅")

print(f"\nPhoBERT (not fine-tuned):")
print(f"  - Top doc: {results_phobert[0][0].metadata.get('article')}")
print(f"  - Score separation: {results_phobert[0][1] - results_phobert[-1][1]:.4f}")
print(f"  - Warnings: Uninitialized weights ⚠️")

print("\n" + "=" * 70)
print("💡 RECOMMENDATION: Use BAAI/bge-reranker-v2-m3 (fine-tuned)")
print("=" * 70)
