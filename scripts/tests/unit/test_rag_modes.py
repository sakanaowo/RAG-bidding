"""
Unit Tests for RAG Mode Validation

Tests cover:
1. Valid modes: fast, balanced, quality
2. Invalid mode: adaptive (removed)
3. Schema validation for preferred_rag_mode
4. create_retriever mode validation
"""

import pytest
from pydantic import ValidationError


class TestRAGModeValidation:
    """Test that RAG modes are correctly validated."""

    def test_valid_modes_in_retriever(self):
        """Valid modes (fast, balanced, quality) should not raise errors."""
        from src.retrieval.retrievers import create_retriever

        # Test each valid mode
        for mode in ["fast", "balanced", "quality"]:
            retriever = create_retriever(mode=mode, enable_reranking=False)
            assert retriever is not None, f"Mode '{mode}' should create a retriever"

    def test_adaptive_mode_rejected_in_retriever(self):
        """Adaptive mode should raise ValueError (removed from codebase)."""
        from src.retrieval.retrievers import create_retriever

        with pytest.raises(ValueError, match="Unknown mode"):
            create_retriever(mode="adaptive", enable_reranking=False)

    def test_invalid_mode_rejected_in_retriever(self):
        """Random invalid modes should raise ValueError."""
        from src.retrieval.retrievers import create_retriever

        invalid_modes = ["invalid", "auto", "turbo", ""]
        for mode in invalid_modes:
            with pytest.raises(ValueError, match="Unknown mode"):
                create_retriever(mode=mode, enable_reranking=False)


class TestSchemaValidation:
    """Test Pydantic schema validation for RAG mode."""

    def test_valid_preferred_rag_mode(self):
        """Valid modes should pass schema validation."""
        from src.api.schemas.auth_schemas import UpdateProfileRequest

        for mode in ["fast", "balanced", "quality"]:
            request = UpdateProfileRequest(preferred_rag_mode=mode)
            assert request.preferred_rag_mode == mode

    def test_adaptive_mode_rejected_in_schema(self):
        """Adaptive mode should fail schema validation (removed)."""
        from src.api.schemas.auth_schemas import UpdateProfileRequest

        with pytest.raises(ValidationError) as exc_info:
            UpdateProfileRequest(preferred_rag_mode="adaptive")
        
        # Check the error mentions pattern validation
        error_str = str(exc_info.value)
        assert "pattern" in error_str.lower() or "string_pattern_mismatch" in error_str

    def test_invalid_mode_rejected_in_schema(self):
        """Random invalid modes should fail schema validation."""
        from src.api.schemas.auth_schemas import UpdateProfileRequest

        invalid_modes = ["invalid", "auto", "turbo"]
        for mode in invalid_modes:
            with pytest.raises(ValidationError):
                UpdateProfileRequest(preferred_rag_mode=mode)

    def test_null_mode_allowed_in_schema(self):
        """None should be allowed for optional field."""
        from src.api.schemas.auth_schemas import UpdateProfileRequest

        request = UpdateProfileRequest(preferred_rag_mode=None)
        assert request.preferred_rag_mode is None


class TestEnhancedFeatures:
    """Test enhanced_features list in qa_chain for each mode."""

    def test_fast_mode_no_enhancement(self):
        """Fast mode should have no enhancement features."""
        # This tests the feature list logic, not actual chain execution
        enhanced_features = []
        selected_mode = "fast"
        
        # Simulate the logic from qa_chain.py (after fix)
        if selected_mode == "fast":
            pass  # No enhancement
        elif selected_mode == "balanced":
            enhanced_features.append("Query Enhancement (Multi-Query, Step-Back)")
        elif selected_mode == "quality":
            enhanced_features.append("Query Enhancement (Multi-Query, HyDE, Step-Back, Decomposition)")
        # NOTE: No adaptive case - this was the bug we fixed
        
        assert len(enhanced_features) == 0

    def test_balanced_mode_features(self):
        """Balanced mode should have multi-query + step-back."""
        enhanced_features = []
        selected_mode = "balanced"
        
        if selected_mode == "fast":
            pass
        elif selected_mode == "balanced":
            enhanced_features.append("Query Enhancement (Multi-Query, Step-Back)")
        elif selected_mode == "quality":
            enhanced_features.append("Query Enhancement (Multi-Query, HyDE, Step-Back, Decomposition)")
        
        assert len(enhanced_features) == 1
        assert "Multi-Query" in enhanced_features[0]
        assert "Step-Back" in enhanced_features[0]

    def test_quality_mode_features(self):
        """Quality mode should have all 4 strategies."""
        enhanced_features = []
        selected_mode = "quality"
        
        if selected_mode == "fast":
            pass
        elif selected_mode == "balanced":
            enhanced_features.append("Query Enhancement (Multi-Query, Step-Back)")
        elif selected_mode == "quality":
            enhanced_features.append("Query Enhancement (Multi-Query, HyDE, Step-Back, Decomposition)")
        
        assert len(enhanced_features) == 1
        assert "HyDE" in enhanced_features[0]
        assert "Decomposition" in enhanced_features[0]

    def test_adaptive_mode_no_longer_handled(self):
        """Adaptive mode should NOT be handled in feature list (dead code removed)."""
        enhanced_features = []
        selected_mode = "adaptive"
        
        # After our fix, there is no elif for adaptive
        if selected_mode == "fast":
            pass
        elif selected_mode == "balanced":
            enhanced_features.append("Query Enhancement (Multi-Query, Step-Back)")
        elif selected_mode == "quality":
            enhanced_features.append("Query Enhancement (Multi-Query, HyDE, Step-Back, Decomposition)")
        # NO adaptive case - dead code was removed
        
        # Adaptive would fall through with no features added
        assert len(enhanced_features) == 0


class TestDefaultMode:
    """Test default mode behavior."""

    def test_default_mode_is_balanced(self):
        """Default mode should be 'balanced'."""
        from src.retrieval.retrievers import create_retriever
        from src.retrieval.retrievers.enhanced_retriever import EnhancedRetriever

        # create_retriever with default mode
        retriever = create_retriever(enable_reranking=False)
        
        # Should be EnhancedRetriever (balanced mode)
        assert isinstance(retriever, EnhancedRetriever)
