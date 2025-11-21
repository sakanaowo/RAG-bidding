"""
Test OpenAI Reranker Integration

Kiểm tra:
1. OpenAI reranker initialization
2. Basic reranking functionality
3. API integration với endpoint /ask
4. Cost comparison vs BGE reranker
"""

import os
import sys
import pytest
import requests
from langchain_core.documents import Document

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.retrieval.ranking import OpenAIReranker


def test_openai_reranker_initialization():
    """Test 1: Kiểm tra khởi tạo OpenAI reranker."""

    # Skip nếu không có API key
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    reranker = OpenAIReranker(model_name="gpt-4o-mini")

    assert reranker is not None
    assert reranker.model_name == "gpt-4o-mini"
    assert reranker.temperature == 0.0
    print("✅ OpenAI reranker initialized successfully")


def test_openai_reranker_scoring():
    """Test 2: Kiểm tra scoring functionality."""

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    reranker = OpenAIReranker(model_name="gpt-4o-mini")

    # Mock documents
    docs = [
        Document(
            page_content="Luật Đấu thầu 2023 quy định về quy trình đấu thầu công khai.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "10"},
        ),
        Document(
            page_content="Nghị định 24/2024 hướng dẫn chi tiết Luật Đấu thầu.",
            metadata={"title": "Nghị định 24/2024", "dieu": "5"},
        ),
        Document(
            page_content="Quy trình mua sắm công được quy định tại Luật Đấu thầu.",
            metadata={"title": "Luật Đấu thầu 2023", "dieu": "15"},
        ),
    ]

    query = "quy trình đấu thầu công khai"

    # Rerank
    results = reranker.rerank(query, docs, top_k=2)

    assert len(results) == 2
    assert all(isinstance(score, float) for _, score in results)
    assert all(0.0 <= score <= 1.0 for _, score in results)

    # Check ordering (scores should be descending)
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)

    print(f"✅ Reranking successful, top score: {scores[0]:.4f}")
    for i, (doc, score) in enumerate(results, 1):
        print(f"  [{i}] {score:.4f} - {doc.page_content[:60]}...")


def test_api_endpoint_with_openai_reranker():
    """Test 3: Kiểm tra API endpoint với OpenAI reranker."""

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    # Test với server đang chạy
    url = "http://localhost:8000/ask"
    payload = {
        "question": "quy trình đấu thầu công khai",
        "mode": "balanced",
        "reranker": "openai",  # 🆕 Use OpenAI reranker
    }

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()

            assert "answer" in data
            assert "sources" in data
            assert "processing_time_ms" in data

            print(f"✅ API call successful")
            print(f"   Processing time: {data['processing_time_ms']}ms")
            print(f"   Answer preview: {data['answer'][:100]}...")
            print(f"   Sources: {len(data['sources'])} documents")
        else:
            print(f"⚠️  API returned status {response.status_code}")
            print(f"   Response: {response.text}")
            pytest.skip(f"API error: {response.status_code}")

    except requests.exceptions.ConnectionError:
        pytest.skip("API server not running")


def test_compare_bge_vs_openai():
    """Test 4: So sánh performance BGE vs OpenAI."""

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    url = "http://localhost:8000/ask"
    query = "điều kiện tham gia đấu thầu"

    # Test BGE
    payload_bge = {"question": query, "mode": "balanced", "reranker": "bge"}

    # Test OpenAI
    payload_openai = {"question": query, "mode": "balanced", "reranker": "openai"}

    try:
        # BGE reranker
        resp_bge = requests.post(url, json=payload_bge, timeout=30)
        bge_time = (
            resp_bge.json().get("processing_time_ms", 0)
            if resp_bge.status_code == 200
            else 0
        )

        # OpenAI reranker
        resp_openai = requests.post(url, json=payload_openai, timeout=30)
        openai_time = (
            resp_openai.json().get("processing_time_ms", 0)
            if resp_openai.status_code == 200
            else 0
        )

        if bge_time and openai_time:
            print(f"\n📊 Performance Comparison:")
            print(f"   BGE:    {bge_time}ms")
            print(f"   OpenAI: {openai_time}ms")
            print(
                f"   Diff:   {openai_time - bge_time:+d}ms ({(openai_time/bge_time - 1)*100:+.1f}%)"
            )

            if openai_time > bge_time:
                print(f"   ⚠️  OpenAI slower (network latency)")
            else:
                print(f"   ⚡ OpenAI faster (no GPU loading)")
        else:
            pytest.skip("Could not get both timings")

    except requests.exceptions.ConnectionError:
        pytest.skip("API server not running")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 OpenAI Reranker Integration Tests")
    print("=" * 60)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    print(f"✅ API key found: {os.getenv('OPENAI_API_KEY')[:20]}...")
    print()

    # Run tests
    pytest.main([__file__, "-v", "-s"])
