"""
Integration Tests for Provider Abstraction Layer (Phase 1)

Tests that verify the provider factories work correctly 
with actual API calls (requires API keys configured).

These tests are marked as slow and may incur API costs.
Run with: pytest tests/integration/test_providers_integration.py -v
"""

import os
import pytest
from unittest.mock import MagicMock


# Skip all tests in this file if no API keys are configured
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
]


def has_openai_key():
    """Check if OpenAI API key is configured."""
    return bool(os.getenv("OPENAI_API_KEY"))


def has_google_key():
    """Check if Google API key is configured."""
    return bool(os.getenv("GOOGLE_API_KEY"))


def has_vertex_credentials():
    """Check if Vertex AI credentials are configured."""
    return bool(
        os.getenv("GOOGLE_CLOUD_PROJECT") or 
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )


class TestLLMProviderIntegration:
    """Integration tests for LLM provider factory."""
    
    @pytest.mark.skipif(not has_openai_key(), reason="OPENAI_API_KEY not configured")
    def test_openai_llm_invoke(self):
        """Test that OpenAI LLM can invoke a simple query."""
        from src.config.llm_provider import get_llm_client, reset_default_llm
        
        reset_default_llm()
        
        llm = get_llm_client(provider="openai")
        response = llm.invoke("Say 'hello' in Vietnamese, just one word")
        
        assert response is not None
        assert hasattr(response, "content")
        assert len(response.content) > 0
        print(f"OpenAI response: {response.content}")
    
    @pytest.mark.skipif(not has_google_key(), reason="GOOGLE_API_KEY not configured")
    def test_gemini_llm_invoke(self):
        """Test that Gemini LLM can invoke a simple query."""
        from src.config.llm_provider import get_llm_client
        
        llm = get_llm_client(provider="gemini")
        response = llm.invoke("Say 'hello' in Vietnamese, just one word")
        
        assert response is not None
        assert hasattr(response, "content")
        assert len(response.content) > 0
        print(f"Gemini response: {response.content}")
    
    @pytest.mark.skipif(not has_vertex_credentials(), reason="Vertex AI credentials not configured")
    def test_vertex_llm_invoke(self):
        """Test that Vertex AI LLM can invoke a simple query."""
        from src.config.llm_provider import get_llm_client
        
        llm = get_llm_client(provider="vertex")
        response = llm.invoke("Say 'hello' in Vietnamese, just one word")
        
        assert response is not None
        assert hasattr(response, "content")
        assert len(response.content) > 0
        print(f"Vertex AI response: {response.content}")


class TestEmbeddingProviderIntegration:
    """Integration tests for Embedding provider factory."""
    
    @pytest.mark.skipif(not has_openai_key(), reason="OPENAI_API_KEY not configured")
    def test_openai_embeddings_query(self):
        """Test that OpenAI embeddings can embed a query."""
        from src.config.embedding_provider import get_embeddings, reset_default_embeddings
        
        reset_default_embeddings()
        
        embeddings = get_embeddings(provider="openai")
        vector = embeddings.embed_query("Đấu thầu là gì?")
        
        assert vector is not None
        assert isinstance(vector, list)
        assert len(vector) == 1536  # text-embedding-3-small dimension
        print(f"OpenAI embedding dimension: {len(vector)}")
    
    @pytest.mark.skipif(not has_openai_key(), reason="OPENAI_API_KEY not configured")
    def test_openai_embeddings_documents(self):
        """Test that OpenAI embeddings can embed multiple documents."""
        from src.config.embedding_provider import get_embeddings
        
        embeddings = get_embeddings(provider="openai")
        docs = [
            "Điều kiện tham gia đấu thầu",
            "Hồ sơ mời thầu cần có những gì?"
        ]
        vectors = embeddings.embed_documents(docs)
        
        assert vectors is not None
        assert len(vectors) == 2
        assert all(len(v) == 1536 for v in vectors)
    
    @pytest.mark.skipif(not has_vertex_credentials(), reason="Vertex AI credentials not configured")
    def test_vertex_embeddings_query(self):
        """Test that Vertex AI embeddings can embed a query."""
        from src.config.embedding_provider import get_embeddings
        
        embeddings = get_embeddings(provider="vertex")
        vector = embeddings.embed_query("Đấu thầu là gì?")
        
        assert vector is not None
        assert isinstance(vector, list)
        assert len(vector) == 768  # text-embedding-004 dimension
        print(f"Vertex AI embedding dimension: {len(vector)}")


class TestRerankerProviderIntegration:
    """Integration tests for Reranker provider factory."""
    
    def test_bge_reranker_rerank(self):
        """Test that BGE reranker can rerank documents."""
        from src.config.reranker_provider import get_reranker, reset_default_reranker
        from langchain_core.documents import Document
        
        reset_default_reranker()
        
        reranker = get_reranker(provider="bge")
        
        # Create test documents
        docs = [
            Document(page_content="Quy trình đấu thầu công khai"),
            Document(page_content="Món ăn Việt Nam ngon nhất"),
            Document(page_content="Điều kiện tham gia đấu thầu quốc tế"),
        ]
        
        results = reranker.rerank(
            query="Điều kiện đấu thầu là gì?",
            documents=docs,
            top_k=2
        )
        
        assert results is not None
        assert len(results) == 2
        
        # Each result should be (Document, score) tuple
        for doc, score in results:
            assert isinstance(doc, Document)
            assert isinstance(score, float)
        
        # First result should be most relevant
        print(f"Top result: {results[0][0].page_content} (score: {results[0][1]:.4f})")
    
    @pytest.mark.skipif(not has_openai_key(), reason="OPENAI_API_KEY not configured")
    def test_openai_reranker_rerank(self):
        """Test that OpenAI reranker can rerank documents."""
        from src.config.reranker_provider import get_reranker
        from langchain_core.documents import Document
        
        reranker = get_reranker(provider="openai")
        
        docs = [
            Document(page_content="Quy trình đấu thầu công khai"),
            Document(page_content="Điều kiện tham gia đấu thầu quốc tế"),
        ]
        
        results = reranker.rerank(
            query="Điều kiện đấu thầu là gì?",
            documents=docs,
            top_k=2
        )
        
        assert results is not None
        assert len(results) == 2


class TestProviderSwitching:
    """Integration tests for switching between providers."""
    
    @pytest.mark.skipif(
        not (has_openai_key() and has_google_key()),
        reason="Both OpenAI and Google API keys required"
    )
    def test_switch_llm_provider(self):
        """Test switching between LLM providers."""
        from src.config.llm_provider import get_llm_client
        
        # Test OpenAI
        openai_llm = get_llm_client(provider="openai")
        openai_response = openai_llm.invoke("Say 'test'")
        
        # Test Gemini
        gemini_llm = get_llm_client(provider="gemini")
        gemini_response = gemini_llm.invoke("Say 'test'")
        
        assert openai_response is not None
        assert gemini_response is not None
        print(f"OpenAI: {openai_response.content}")
        print(f"Gemini: {gemini_response.content}")
    
    def test_reranker_fallback(self):
        """Test that BGE reranker works as fallback."""
        from src.config.reranker_provider import get_reranker
        from langchain_core.documents import Document
        
        # Request vertex, should fallback to BGE
        reranker = get_reranker(provider="vertex")
        
        docs = [Document(page_content="Test document")]
        results = reranker.rerank("test query", docs, top_k=1)
        
        assert results is not None
        assert len(results) == 1
