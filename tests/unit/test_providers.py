"""
Unit Tests for Provider Abstraction Layer (Phase 1)

Tests the factory pattern implementations for:
- LLM Provider (llm_provider.py)
- Embedding Provider (embedding_provider.py)
- Reranker Provider (reranker_provider.py)
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestLLMProvider:
    """Tests for LLM provider factory."""
    
    def test_llm_provider_enum_values(self):
        """Test that LLMProvider enum has correct values."""
        from src.config.llm_provider import LLMProvider
        
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.VERTEX_AI.value == "vertex"
        assert LLMProvider.GEMINI.value == "gemini"
    
    def test_get_llm_client_openai(self):
        """Test OpenAI LLM client creation."""
        from src.config.llm_provider import get_llm_client, reset_default_llm
        
        # Reset any cached client
        reset_default_llm()
        
        client = get_llm_client(provider="openai")
        
        # Verify it's a ChatOpenAI instance
        assert client is not None
        assert hasattr(client, "invoke")
    
    def test_get_llm_client_invalid_provider(self):
        """Test error handling for invalid provider."""
        from src.config.llm_provider import get_llm_client
        
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client(provider="invalid_provider")
    
    def test_get_llm_client_with_temperature(self):
        """Test LLM client creation with custom temperature."""
        from src.config.llm_provider import get_llm_client
        
        client = get_llm_client(provider="openai", temperature=0.7)
        
        assert client is not None
        # Temperature should be set
        assert client.temperature == 0.7
    
    def test_default_llm_singleton(self):
        """Test that get_default_llm returns singleton."""
        from src.config.llm_provider import get_default_llm, reset_default_llm
        
        reset_default_llm()
        
        client1 = get_default_llm()
        client2 = get_default_llm()
        
        # Should be the same instance
        assert client1 is client2
    
    def test_reset_default_llm(self):
        """Test that reset_default_llm clears singleton."""
        from src.config.llm_provider import get_default_llm, reset_default_llm
        
        client1 = get_default_llm()
        reset_default_llm()
        client2 = get_default_llm()
        
        # Should be different instances after reset
        assert client1 is not client2


class TestEmbeddingProvider:
    """Tests for Embedding provider factory."""
    
    def test_embedding_provider_enum_values(self):
        """Test that EmbeddingProvider enum has correct values."""
        from src.config.embedding_provider import EmbeddingProvider
        
        assert EmbeddingProvider.OPENAI.value == "openai"
        assert EmbeddingProvider.VERTEX_AI.value == "vertex"
    
    def test_embedding_dimensions_mapping(self):
        """Test embedding dimension lookup."""
        from src.config.embedding_provider import (
            get_embedding_dimension,
            EMBEDDING_DIMENSIONS
        )
        
        # OpenAI models
        assert get_embedding_dimension("text-embedding-3-small") == 1536
        assert get_embedding_dimension("text-embedding-3-large") == 3072
        
        # Vertex AI models
        assert get_embedding_dimension("text-embedding-004") == 768
        assert get_embedding_dimension("text-embedding-005") == 768
        
        # Gemini models
        assert get_embedding_dimension("gemini-embedding-001") == 1536
        
        # Unknown model should return default
        assert get_embedding_dimension("unknown-model") == 768
    
    def test_get_embeddings_openai(self):
        """Test OpenAI embeddings creation."""
        from src.config.embedding_provider import get_embeddings, reset_default_embeddings
        
        reset_default_embeddings()
        
        embeddings = get_embeddings(provider="openai")
        
        assert embeddings is not None
        assert hasattr(embeddings, "embed_query")
        assert hasattr(embeddings, "embed_documents")
    
    def test_get_embeddings_invalid_provider(self):
        """Test error handling for invalid provider."""
        from src.config.embedding_provider import get_embeddings
        
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            get_embeddings(provider="invalid_provider")
    
    def test_default_embeddings_singleton(self):
        """Test that get_default_embeddings returns singleton."""
        from src.config.embedding_provider import (
            get_default_embeddings, 
            reset_default_embeddings,
            get_embeddings
        )
        from src.config.models import settings
        
        reset_default_embeddings()
        
        # Try to get embeddings, skip test if provider package not installed
        try:
            emb1 = get_default_embeddings()
            emb2 = get_default_embeddings()
            assert emb1 is emb2
        except ImportError as e:
            pytest.skip(f"Embedding provider package not installed: {e}")


class TestRerankerProvider:
    """Tests for Reranker provider factory."""
    
    def test_reranker_provider_enum_values(self):
        """Test that RerankerProvider enum has correct values."""
        from src.config.reranker_provider import RerankerProvider
        
        assert RerankerProvider.BGE.value == "bge"
        assert RerankerProvider.OPENAI.value == "openai"
        assert RerankerProvider.VERTEX_AI.value == "vertex"
    
    def test_get_reranker_bge(self):
        """Test BGE reranker creation."""
        from src.config.reranker_provider import get_reranker, reset_default_reranker
        
        reset_default_reranker()
        
        reranker = get_reranker(provider="bge")
        
        assert reranker is not None
        assert hasattr(reranker, "rerank")
    
    def test_get_reranker_openai(self):
        """Test OpenAI reranker creation."""
        from src.config.reranker_provider import get_reranker
        
        reranker = get_reranker(provider="openai")
        
        assert reranker is not None
        assert hasattr(reranker, "rerank")
    
    def test_get_reranker_invalid_provider(self):
        """Test error handling for invalid provider."""
        from src.config.reranker_provider import get_reranker
        
        with pytest.raises(ValueError, match="Unknown reranker provider"):
            get_reranker(provider="invalid_provider")
    
    def test_vertex_reranker_requires_project(self):
        """Test that vertex reranker requires GOOGLE_CLOUD_PROJECT."""
        from src.config.reranker_provider import get_reranker
        from src.config.models import settings
        
        # If project is not set, should raise ValueError
        if not settings.google_cloud_project:
            with pytest.raises(ValueError, match="GOOGLE_CLOUD_PROJECT is required"):
                get_reranker(provider="vertex")
        else:
            # If project is set, reranker should be created
            reranker = get_reranker(provider="vertex")
            assert reranker is not None
            assert hasattr(reranker, "rerank")


class TestProviderSettings:
    """Tests for provider settings in models.py."""
    
    def test_provider_settings_exist(self):
        """Test that provider settings are defined."""
        from src.config.models import settings
        
        assert hasattr(settings, "llm_provider")
        assert hasattr(settings, "embed_provider")
        assert hasattr(settings, "reranker_provider")
    
    def test_vertex_settings_exist(self):
        """Test that Vertex AI settings are defined."""
        from src.config.models import settings
        
        assert hasattr(settings, "google_cloud_project")
        assert hasattr(settings, "google_cloud_location")
        assert hasattr(settings, "vertex_llm_model")
        assert hasattr(settings, "vertex_embed_model")
    
    def test_gemini_settings_exist(self):
        """Test that Gemini settings are defined."""
        from src.config.models import settings
        
        assert hasattr(settings, "gemini_model")
    
    def test_embed_dimensions_setting(self):
        """Test that embed_dimensions setting exists."""
        from src.config.models import settings
        
        assert hasattr(settings, "embed_dimensions")
        assert isinstance(settings.embed_dimensions, int)
        assert settings.embed_dimensions > 0
    
    def test_vertex_reranker_model_setting(self):
        """Test that vertex_reranker_model setting exists."""
        from src.config.models import settings
        
        assert hasattr(settings, "vertex_reranker_model")
        assert "semantic-ranker" in settings.vertex_reranker_model
    
    def test_default_provider_values(self):
        """Test default provider values."""
        from src.config.models import settings
        
        # These should be the defaults if not set in .env
        # (actual values may differ based on .env)
        assert settings.llm_provider in ["openai", "vertex", "gemini"]
        assert settings.embed_provider in ["openai", "vertex"]
        assert settings.reranker_provider in ["bge", "openai", "vertex"]
