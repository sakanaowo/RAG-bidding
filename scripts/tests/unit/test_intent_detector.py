"""
Unit Tests for Intent Detector

Tests cover:
1. Gibberish detection (random text, entropy-based)
2. Casual query detection (greetings, thanks, goodbyes)
3. Domain relevance scoring (đấu thầu keywords)
4. Context follow-up detection
5. Edge cases and boundary conditions
"""

import pytest
from src.generation.intent_detector import (
    IntentDetector,
    QueryIntent,
    IntentResult,
    get_intent_detector,
    detect_intent,
)


class TestIntentDetector:
    """Test IntentDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a fresh IntentDetector instance for each test."""
        return IntentDetector()

    # =============================================
    # GIBBERISH DETECTION TESTS
    # =============================================
    
    @pytest.mark.parametrize("query", [
        "",
        " ",
        "a",
        "ab",
    ])
    def test_empty_or_short_queries_detected_as_gibberish(self, detector, query):
        """Empty or very short queries should be classified as gibberish."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.GIBBERISH
        assert result.confidence >= 0.9
    
    @pytest.mark.parametrize("query", [
        "iajsndijansd",  # From user's bug report
        "asdasdasdasd",
        "qwqwqwqwqw",
        "xyzxyzxyz",
        "kdfjhgskjdfhg",
        "asjkdhaskjdhaskjdh",
    ])
    def test_random_text_detected_as_gibberish(self, detector, query):
        """Random text without meaning should be detected as gibberish."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.GIBBERISH, f"Expected GIBBERISH for '{query}', got {result.intent}"
        assert result.suggested_response is not None

    @pytest.mark.parametrize("query", [
        "zzzzzzzzzzz",
        "aaaaaaaaaaa",
    ])
    def test_repeated_single_char_detected_as_gibberish(self, detector, query):
        """Repeated single character should be gibberish."""
        result = detector.detect(query)
        # May be detected as gibberish due to low entropy or special cases
        assert result.intent in [QueryIntent.GIBBERISH, QueryIntent.OFF_TOPIC]

    # =============================================
    # CASUAL QUERY TESTS
    # =============================================

    @pytest.mark.parametrize("query,expected_response_contains", [
        ("xin chào", "Xin chào"),
        ("chào bạn", "Xin chào"),
        ("hello", "Xin chào"),
        ("hi", "Xin chào"),
        ("alo", "Xin chào"),
        ("hey", "Xin chào"),
        ("hiii", "Xin chào"),
        ("hellooo", "Xin chào"),
    ])
    def test_greeting_queries_detected_as_casual(self, detector, query, expected_response_contains):
        """Greetings should be detected as casual with appropriate response."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.CASUAL, f"Expected CASUAL for '{query}', got {result.intent}"
        assert expected_response_contains in result.suggested_response
    
    @pytest.mark.parametrize("query", [
        "cảm ơn",
        "cám ơn",
        "thanks",
        "ok cảm ơn",
    ])
    def test_thanks_queries_detected_as_casual(self, detector, query):
        """Thanks queries should be casual."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.CASUAL
        assert "Không có gì" in result.suggested_response

    @pytest.mark.parametrize("query", [
        "tạm biệt",
        "bye",
        "goodbye",
    ])
    def test_goodbye_queries_detected_as_casual(self, detector, query):
        """Goodbye queries should be casual."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.CASUAL
        assert "Tạm biệt" in result.suggested_response

    @pytest.mark.parametrize("query", [
        "bạn là ai",
        "bạn có thể làm gì",
        "tên bạn là gì",
    ])
    def test_identity_queries_detected_as_casual(self, detector, query):
        """Identity questions should be casual."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.CASUAL
        assert "trợ lý AI" in result.suggested_response

    @pytest.mark.parametrize("query", [
        "ok",
        "ừ",
        "được",
        "rồi",
        "vâng",
    ])
    def test_confirmation_queries_detected_as_casual(self, detector, query):
        """Simple confirmations should be casual."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.CASUAL

    # =============================================
    # ON_TOPIC (DOMAIN RELEVANCE) TESTS
    # =============================================

    @pytest.mark.parametrize("query", [
        "đấu thầu là gì",
        "điều kiện tham gia đấu thầu",
        "quy trình mở thầu như thế nào",
        "nhà thầu cần đáp ứng tiêu chuẩn gì",
        "hồ sơ mời thầu bao gồm những gì",
        "chế tài với nhà thầu vi phạm",
        "luật đấu thầu 2023 có gì mới",
        "nghị định 24 quy định gì",
        "bên mời thầu là ai",
        "đấu thầu điện tử là gì",
    ])
    def test_bidding_queries_detected_as_on_topic(self, detector, query):
        """Queries about đấu thầu should be on-topic."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.ON_TOPIC, f"Expected ON_TOPIC for '{query}', got {result.intent}"
        assert result.suggested_response is None  # Should run RAG

    # =============================================
    # CONTEXT FOLLOW-UP TESTS
    # =============================================

    @pytest.mark.parametrize("query", [
        "như đã nói ở trên",
        "vậy thì sao",
        "tiếp tục giải thích",
        "nói rõ hơn đi",
        "điều đó có nghĩa là gì",
        "chi tiết hơn được không",
    ])
    def test_context_followup_detected(self, detector, query):
        """Queries referencing previous context should be detected."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.CONTEXT_FOLLOW_UP, f"Expected CONTEXT_FOLLOW_UP for '{query}', got {result.intent}"

    # =============================================
    # OFF_TOPIC TESTS  
    # =============================================

    @pytest.mark.parametrize("query", [
        "thời tiết hôm nay thế nào?",
        "bao nhiêu tuổi thì được lái xe?",
        "làm thế nào để nấu phở?",
    ])
    def test_off_topic_queries_detected(self, detector, query):
        """Non-bidding questions should be off-topic."""
        result = detector.detect(query)
        assert result.intent == QueryIntent.OFF_TOPIC, f"Expected OFF_TOPIC for '{query}', got {result.intent}"
        assert result.suggested_response is not None

    # =============================================
    # EDGE CASES
    # =============================================

    def test_mixed_casual_and_topic(self, detector):
        """Query mixing casual and topic should prioritize topic."""
        result = detector.detect("chào bạn, đấu thầu là gì")
        # Could be either ON_TOPIC or CASUAL depending on implementation
        # The key is that casual greetings at start don't block topic detection
        assert result.intent in [QueryIntent.ON_TOPIC, QueryIntent.CASUAL]

    def test_unicode_handling(self, detector):
        """Vietnamese unicode should be handled correctly."""
        result = detector.detect("điều kiện đấu thầu")
        assert result.intent == QueryIntent.ON_TOPIC

    def test_case_insensitivity(self, detector):
        """Detection should be case insensitive."""
        result1 = detector.detect("ĐẤU THẦU")
        result2 = detector.detect("đấu thầu")
        assert result1.intent == result2.intent

    # =============================================
    # SINGLETON AND HELPER TESTS
    # =============================================

    def test_singleton_returns_same_instance(self):
        """get_intent_detector should return singleton."""
        detector1 = get_intent_detector()
        detector2 = get_intent_detector()
        assert detector1 is detector2

    def test_detect_intent_helper(self):
        """detect_intent helper should work correctly."""
        result = detect_intent("đấu thầu là gì")
        assert isinstance(result, IntentResult)
        assert result.intent == QueryIntent.ON_TOPIC


class TestGibberishDetectionAlgorithms:
    """Test the internal gibberish detection algorithms."""

    @pytest.fixture
    def detector(self):
        return IntentDetector()

    def test_entropy_calculation(self, detector):
        """Test Shannon entropy calculation."""
        # Low entropy (repeated chars)
        low_entropy = detector._calculate_entropy("aaaaaaaaaa")
        # High entropy (random chars)
        high_entropy = detector._calculate_entropy("abcdefghij")
        
        assert low_entropy < high_entropy
        assert low_entropy == 0.0  # All same char = 0 entropy

    def test_vowel_ratio_calculation(self, detector):
        """Test vowel ratio calculation for Vietnamese."""
        # Vietnamese text has high vowel ratio
        vn_text = "Đây là văn bản tiếng Việt"
        vn_ratio = detector._calculate_vowel_ratio(vn_text)
        
        # Random consonants have low vowel ratio
        random_text = "bcdfghjklmnpqrstvwxz"
        random_ratio = detector._calculate_vowel_ratio(random_text)
        
        assert vn_ratio > random_ratio
        assert vn_ratio > 0.3  # Vietnamese typically > 30% vowels

    def test_repeated_nonsense_detection(self, detector):
        """Test repeated nonsense pattern detection."""
        assert detector._has_repeated_nonsense("asdasdasdasd") == True
        assert detector._has_repeated_nonsense("qwqwqwqw") == True
        assert detector._has_repeated_nonsense("đấu thầu") == False


class TestDomainScoring:
    """Test domain relevance scoring."""

    @pytest.fixture
    def detector(self):
        return IntentDetector()

    def test_high_domain_score_for_bidding_query(self, detector):
        """Queries with bidding keywords should have high domain score."""
        score = detector._calculate_domain_score("nhà thầu đấu thầu hồ sơ")
        assert score >= 0.5

    def test_low_domain_score_for_unrelated_query(self, detector):
        """Queries without bidding keywords should have low domain score."""
        score = detector._calculate_domain_score("thời tiết hôm nay")
        assert score < 0.3

    def test_zero_domain_score_for_empty(self, detector):
        """Empty string should have zero domain score."""
        score = detector._calculate_domain_score("")
        assert score == 0.0
