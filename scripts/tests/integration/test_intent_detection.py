"""
Integration Tests for Intent Detection in Conversation Flow

Tests the full flow:
1. Intent detection → conversation_service
2. Gibberish queries don't trigger RAG
3. Context only attached for CONTEXT_FOLLOW_UP
"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from src.generation.intent_detector import (
    IntentDetector,
    QueryIntent,
    get_intent_detector,
)


class TestIntentDetectionIntegration:
    """Integration tests for intent detection in conversation flow."""

    @pytest.fixture
    def detector(self):
        return IntentDetector()

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return MagicMock()

    def test_gibberish_does_not_trigger_rag(self, detector):
        """Gibberish queries should return GIBBERISH intent and skip RAG."""
        gibberish_queries = [
            "iajsndijansd",  # The original bug case
            "asdasdasdasd",
            "qwqwqwqw",
            "xyzxyzxyz",
        ]
        
        for query in gibberish_queries:
            result = detector.detect(query)
            assert result.intent == QueryIntent.GIBBERISH, f"Expected GIBBERISH for '{query}'"
            assert result.suggested_response is not None

    def test_valid_bidding_query_triggers_rag(self, detector):
        """Valid bidding queries should return ON_TOPIC and trigger RAG."""
        valid_queries = [
            "điều kiện tham gia đấu thầu là gì",
            "chế tài với nhà thầu vi phạm",
            "quy trình nộp hồ sơ dự thầu",
        ]
        
        for query in valid_queries:
            result = detector.detect(query)
            assert result.intent == QueryIntent.ON_TOPIC, f"Expected ON_TOPIC for '{query}'"
            assert result.suggested_response is None  # RAG should handle

    def test_context_followup_uses_context(self, detector):
        """Context follow-up queries should use conversation context."""
        followup_queries = [
            "như đã nói ở trên",
            "nói rõ hơn về điều đó",
            "tiếp tục giải thích",
        ]
        
        for query in followup_queries:
            result = detector.detect(query)
            assert result.intent == QueryIntent.CONTEXT_FOLLOW_UP, f"Expected CONTEXT_FOLLOW_UP for '{query}'"

    def test_off_topic_redirects_to_domain(self, detector):
        """Off-topic queries should redirect to domain."""
        off_topic_queries = [
            "thời tiết hôm nay thế nào?",
            "làm thế nào để nấu phở?",
        ]
        
        for query in off_topic_queries:
            result = detector.detect(query)
            assert result.intent == QueryIntent.OFF_TOPIC, f"Expected OFF_TOPIC for '{query}'"
            assert "đấu thầu" in result.suggested_response.lower()

    def test_intent_detector_singleton(self):
        """Intent detector should use singleton pattern."""
        detector1 = get_intent_detector()
        detector2 = get_intent_detector()
        assert detector1 is detector2


class TestConversationServiceIntegration:
    """
    Integration tests for conversation_service with intent detection.
    
    These tests mock the database and verify the flow.
    """

    def test_intent_detection_import(self):
        """Verify IntentDetector can be imported in conversation_service."""
        from src.api.services.conversation_service import (
            ConversationService,
            get_intent_detector,
            QueryIntent,
        )
        assert get_intent_detector is not None
        assert QueryIntent is not None

    def test_casual_queries_skip_rag(self):
        """Casual queries should skip RAG and return direct response."""
        detector = get_intent_detector()
        result = detector.detect("xin chào")
        assert result.intent == QueryIntent.CASUAL
        assert "Xin chào" in result.suggested_response


class TestBugReproduction:
    """
    Reproduce the original bug from the user's report.
    
    Bug: User sends "iajsndijansd" in conversation with previous context
          about "chế tài nhà thầu vi phạm". System returns content from
          context instead of detecting gibberish.
    """

    def test_gibberish_with_previous_context_does_not_use_context(self):
        """
        When user sends gibberish, system should NOT use conversation context.
        
        This is the main bug fix.
        """
        detector = get_intent_detector()
        
        # Simulate the bug scenario
        gibberish_query = "iajsndijansd"
        previous_context = "Chế tài với nhà thầu vi phạm được quy định như sau..."
        
        # Intent detection should happen BEFORE context is attached
        result = detector.detect(gibberish_query)
        
        # The query should be detected as GIBBERISH
        assert result.intent == QueryIntent.GIBBERISH
        
        # The response should be the polite error, not context-based
        assert "không hiểu" in result.suggested_response.lower()
        assert "nhà thầu" not in result.suggested_response.lower()

    def test_valid_query_after_context_uses_rag(self):
        """
        When user sends valid query after conversation, RAG should work.
        """
        detector = get_intent_detector()
        
        # Valid query about bidding
        query = "còn về quy trình nộp thầu thì sao?"
        
        result = detector.detect(query)
        
        # Should be ON_TOPIC or CONTEXT_FOLLOW_UP, and run RAG
        assert result.intent in [QueryIntent.ON_TOPIC, QueryIntent.CONTEXT_FOLLOW_UP]
        assert result.suggested_response is None  # RAG handles this
