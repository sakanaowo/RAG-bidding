"""
Intent Detection Module for RAG Pipeline

Detects query intent BEFORE attaching conversation context to avoid:
1. Gibberish queries polluting RAG with irrelevant context
2. Off-topic queries triggering unnecessary RAG retrieval
3. Casual queries being over-processed

Query Intents:
- CASUAL: Greetings, thanks, goodbyes
- ON_TOPIC: Valid questions about đấu thầu
- OFF_TOPIC: Valid questions but not about đấu thầu domain
- GIBBERISH: Random/meaningless text
- CONTEXT_FOLLOW_UP: References previous conversation ("như đã nói", "ở trên")
"""

import re
import math
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Classification of user query intent."""
    CASUAL = "casual"
    ON_TOPIC = "on_topic"
    OFF_TOPIC = "off_topic"
    GIBBERISH = "gibberish"
    CONTEXT_FOLLOW_UP = "context_follow_up"


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: QueryIntent
    confidence: float
    reason: str
    suggested_response: Optional[str] = None


class IntentDetector:
    """
    Detect user query intent for smarter RAG processing.
    
    Order of checks:
    1. Empty/too short → GIBBERISH
    2. Entropy check → GIBBERISH (random text)
    3. Casual patterns → CASUAL
    4. Context follow-up patterns → CONTEXT_FOLLOW_UP
    5. Domain keywords → ON_TOPIC or OFF_TOPIC
    """
    
    # Đấu thầu domain keywords (Vietnamese bidding law)
    DOMAIN_KEYWORDS = [
        # Core terms
        "đấu thầu", "nhà thầu", "gói thầu", "hồ sơ mời thầu", "hồ sơ dự thầu",
        "chủ đầu tư", "bên mời thầu", "đánh giá thầu", "xét thầu", "trúng thầu",
        "mua sắm công", "mua sắm tập trung", "đấu giá", "chỉ định thầu",
        # Legal references
        "luật đấu thầu", "nghị định", "thông tư", "điều", "khoản", "điểm",
        "quy định", "pháp luật", "văn bản", "hướng dẫn",
        # Procedures
        "quy trình", "thủ tục", "hồ sơ", "điều kiện", "tiêu chuẩn", "tiêu chí",
        "năng lực", "kinh nghiệm", "tài chính", "kỹ thuật",
        # Entities
        "nhà thầu phụ", "nhà thầu chính", "liên danh", "tư vấn", "giám sát",
        # Actions
        "nộp", "đăng ký", "tham gia", "khiếu nại", "xử lý vi phạm", "chế tài",
        # E-procurement
        "hệ thống mạng", "đấu thầu điện tử", "đấu thầu qua mạng",
    ]
    
    # Context follow-up patterns (query references previous context)
    CONTEXT_PATTERNS = [
        r"(như|giống|tương tự)\s*(đã\s*)?(nói|đề cập|trình bày|giải thích)",
        r"(ở|trong|tại)\s*(trên|trước|phần trước)",
        r"(vậy\s+thì|thế\s+thì|như\s+vậy)",
        r"(tiếp tục|nói\s+thêm|giải thích\s+rõ)",
        r"(cái\s+)?đó\s+(là|có|được)",
        r"(điều|khoản|quy định)\s+(đó|này|trên)",
        r"^(rồi|vậy|thế|à|ừ|được)\s*\?*$",
        r"(chi tiết|cụ thể|rõ)\s+hơn",
        r"ý\s+(bạn|anh|chị)\s+là",
        # NEW: Examples and clarifications
        r"ví\s+dụ\s+(cụ\s+thể|thực\s+tế)?",  # "ví dụ", "ví dụ cụ thể"
        r"(lấy|cho|nêu)\s+ví\s+dụ",  # "lấy ví dụ", "cho ví dụ"
        r"cụ\s+thể\s+(là|như)\s+(thế\s+nào|gì|sao)",  # "cụ thể là gì"
        r"^(nó|đó|vậy|thế)\s+(là\s+)?(gì|sao)\s*\??$",  # "đó là gì", "nó là gì"
        r"(giải\s+thích|nói)\s+(rõ|kỹ|thêm)",  # "giải thích rõ"
        r"(có\s+thể\s+)?(cho\s+)?ví\s+dụ",  # "có thể cho ví dụ"
    ]
    
    # Casual patterns (greetings, thanks, etc.)
    CASUAL_PATTERNS = {
        "greeting": [
            r"^(xin\s+)?chào",
            r"^h+i+$",
            r"^h+e+l+o+$",
            r"^a+l+o+$",
            r"^hey+$",
            r"chào\s+(buổi\s+)?(sáng|trưa|chiều|tối)",
            r"^good\s+(morning|afternoon|evening)$",
        ],
        "thanks": [
            r"(cảm|cám)\s*ơn",
            r"^thanks?$",
            r"^tks$",
            r"^ok\s+(cảm|cám)\s*ơn",
        ],
        "goodbye": [
            r"tạm\s+biệt",
            r"^bye+$",
            r"^goodbye$",
            r"hẹn\s+gặp\s+lại",
        ],
        "identity": [
            r"bạn\s+là\s+(ai|gì)",
            r"tên\s+bạn",
            r"(ai|gì)\s+tạo\s+ra\s+bạn",
            r"bạn\s+(có\s+thể\s+)?làm\s+(được\s+)?gì",
        ],
        "confirmation": [
            r"^(ok|ừ|uh|được|rồi|vâng|dạ|yes|no|không)$",
            r"^ừ$",  # Single char Vietnamese confirmation
        ],
    }
    
    # Direct responses for casual intents
    CASUAL_RESPONSES = {
        "greeting": "Xin chào! 👋 Tôi là trợ lý chuyên về pháp luật đấu thầu Việt Nam. Bạn cần hỏi gì về đấu thầu, tôi sẵn sàng hỗ trợ!",
        "thanks": "Không có gì! 😊 Nếu bạn có thêm câu hỏi về đấu thầu, cứ hỏi nhé!",
        "goodbye": "Tạm biệt! 👋 Hẹn gặp lại bạn. Chúc bạn một ngày tốt lành!",
        "identity": (
            "Tôi là trợ lý AI chuyên về pháp luật đấu thầu Việt Nam. 📚\n\n"
            "Tôi có thể giúp bạn:\n"
            "- Tra cứu quy định trong Luật Đấu thầu, Nghị định, Thông tư\n"
            "- Giải đáp thắc mắc về quy trình đấu thầu\n"
            "- Tìm hiểu điều kiện, tiêu chuẩn cho nhà thầu\n"
            "- Hướng dẫn về hồ sơ mời thầu, đánh giá thầu\n\n"
            "Hãy đặt câu hỏi cụ thể về đấu thầu để tôi hỗ trợ bạn!"
        ),
        "confirmation": "Bạn có câu hỏi gì khác về đấu thầu không? Tôi sẵn sàng hỗ trợ!",
    }
    
    # Gibberish response
    GIBBERISH_RESPONSE = (
        "Xin lỗi, tôi không hiểu câu hỏi của bạn. 🤔\n\n"
        "Bạn có thể đặt lại câu hỏi rõ ràng hơn về đấu thầu được không?"
    )
    
    # Off-topic response
    OFF_TOPIC_RESPONSE = (
        "Tôi chỉ hỗ trợ về pháp luật đấu thầu Việt Nam. 📋\n\n"
        "Bạn có thể hỏi tôi về:\n"
        "- Quy trình đấu thầu\n"
        "- Điều kiện tham gia đấu thầu\n"
        "- Hồ sơ mời thầu, đánh giá thầu\n"
        "- Các quy định pháp luật liên quan"
    )
    
    def __init__(
        self,
        min_query_length: int = 3,  # Increased from 2 to filter 'ab' etc.
        max_entropy_threshold: float = 4.5,  # Higher = more random
        min_domain_confidence: float = 0.3,
    ):
        """
        Initialize IntentDetector.
        
        Args:
            min_query_length: Minimum characters for valid query
            max_entropy_threshold: Shannon entropy threshold for gibberish detection
            min_domain_confidence: Minimum keyword match ratio for on-topic
        """
        self.min_query_length = min_query_length
        self.max_entropy_threshold = max_entropy_threshold
        self.min_domain_confidence = min_domain_confidence
        
        # Compile regex patterns for performance
        self._context_patterns = [re.compile(p, re.IGNORECASE) for p in self.CONTEXT_PATTERNS]
        self._casual_patterns = {
            category: [re.compile(p, re.IGNORECASE) for p in patterns]
            for category, patterns in self.CASUAL_PATTERNS.items()
        }
    
    def detect(
        self,
        query: str,
        conversation_context: Optional[str] = None,
    ) -> IntentResult:
        """
        Detect the intent of a user query.
        
        Args:
            query: User query text
            conversation_context: Previous conversation context (optional)
        
        Returns:
            IntentResult with intent classification

        NOTE: conversation_context is provided for potential future use
        in context-aware intent detection, but currently not used.
        """
        if not query:
            return IntentResult(
                intent=QueryIntent.GIBBERISH,
                confidence=1.0,
                reason="Empty query",
                suggested_response=self.GIBBERISH_RESPONSE,
            )
        
        query_stripped = query.strip()
        query_lower = query_stripped.lower()
        
        # 1. Check casual patterns FIRST (before length check)
        # This allows single-char Vietnamese confirmations like "ừ" to be detected
        casual_result = self._check_casual(query_lower)
        if casual_result:
            return casual_result
        
        # 2. Check too short (after casual check)
        if len(query_stripped) < self.min_query_length:
            return IntentResult(
                intent=QueryIntent.GIBBERISH,
                confidence=0.9,
                reason=f"Query too short ({len(query_stripped)} chars)",
                suggested_response=self.GIBBERISH_RESPONSE,
            )
        
        # 3. Check gibberish (entropy-based and heuristics)
        if self._is_gibberish(query_stripped):
            return IntentResult(
                intent=QueryIntent.GIBBERISH,
                confidence=0.85,
                reason="High entropy / random text detected",
                suggested_response=self.GIBBERISH_RESPONSE,
            )
        
        # 4. Check context follow-up (before domain check)
        if self._is_context_follow_up(query_lower):
            return IntentResult(
                intent=QueryIntent.CONTEXT_FOLLOW_UP,
                confidence=0.8,
                reason="Query references previous context",
                suggested_response=None,  # Should use context
            )
        
        # 5. Check domain relevance
        domain_score = self._calculate_domain_score(query_lower)
        
        if domain_score >= self.min_domain_confidence:
            return IntentResult(
                intent=QueryIntent.ON_TOPIC,
                confidence=min(domain_score + 0.3, 1.0),
                reason=f"Domain keywords found (score: {domain_score:.2f})",
                suggested_response=None,  # Run RAG
            )
        
        # 6. If has Vietnamese question words but no domain keywords → might be off-topic
        if self._has_question_pattern(query_lower) and domain_score < 0.1:
            return IntentResult(
                intent=QueryIntent.OFF_TOPIC,
                confidence=0.6,
                reason="Question pattern but no domain keywords",
                suggested_response=self.OFF_TOPIC_RESPONSE,
            )
        
        # 7. Default: Assume on-topic with lower confidence (let RAG handle it)
        return IntentResult(
            intent=QueryIntent.ON_TOPIC,
            confidence=0.5,
            reason="Default classification - no clear pattern",
            suggested_response=None,
        )
    
    def _is_gibberish(self, text: str) -> bool:
        """
        Detect gibberish using multiple heuristics.
        
        Heuristics:
        1. Shannon entropy (high entropy = random)
        2. Vowel ratio (Vietnamese should have ~40% vowels)
        3. Repeated character patterns
        4. No Vietnamese diacritics in long text
        5. All consonants check
        """
        # Check for repeated nonsense patterns first (quick check)
        if self._has_repeated_nonsense(text):
            logger.debug(f"Repeated nonsense pattern for '{text[:30]}...'")
            return True
        
        # Calculate Shannon entropy
        entropy = self._calculate_entropy(text)
        
        # Vietnamese text typically has entropy 3.5-4.2
        # Random Latin text has entropy around 3.8-4.3
        if entropy > self.max_entropy_threshold:
            logger.debug(f"High entropy detected: {entropy:.2f} for '{text[:30]}...'")
            return True
        
        # For longer text, check multiple heuristics
        if len(text) > 6:
            vowel_ratio = self._calculate_vowel_ratio(text)
            has_diacritics = self._has_vietnamese_diacritics(text)
            
            # Check if it's pure Latin text without Vietnamese characteristics
            # "iajsndijansd" has vowels (a, i) but looks random
            if not has_diacritics and self._is_pure_latin_gibberish(text):
                logger.debug(f"Latin gibberish detected for '{text[:30]}...'")
                return True
            
            # Pure consonants or very low vowel ratio = gibberish
            if vowel_ratio < 0.20:
                # If no Vietnamese diacritics and low vowels, likely gibberish
                if not has_diacritics:
                    logger.debug(f"Low vowel ratio ({vowel_ratio:.2f}) + no diacritics for '{text[:30]}...'")
                    return True
            
            # Check if text is only Latin letters without any Vietnamese characters
            # Vietnamese queries typically have at least some diacritics
            if len(text) > 10 and not has_diacritics:
                # Check if it looks like random keyboard mashing
                if self._looks_like_keyboard_mash(text):
                    logger.debug(f"Keyboard mash detected for '{text[:30]}...'")
                    return True
        
        return False
    
    def _is_pure_latin_gibberish(self, text: str) -> bool:
        """
        Detect pure Latin text that looks like random gibberish.
        
        Vietnamese text without diacritics still follows patterns:
        - Common word structures (consonant-vowel patterns)
        - Recognizable syllables
        - No unusual consonant clusters
        
        Random text lacks these patterns AND has unusual clusters.
        """
        text_lower = text.lower().replace(" ", "")
        
        if len(text_lower) < 7:
            return False
        
        # Check if all characters are basic Latin letters
        if not all(c.isalpha() and ord(c) < 128 for c in text_lower):
            return False  # Has non-Latin chars, let other checks handle
        
        # Check for unusual consonant clusters (not found in Vietnamese)
        # Vietnamese has max 2-3 consonant clusters: "tr", "th", "ch", "ng", "nh", "kh", "ph"
        consonants = set("bcdfghjklmnpqrstvwxz")
        
        # Find consonant cluster lengths
        max_cluster = 0
        current_cluster = 0
        cluster_count = 0
        
        for c in text_lower:
            if c in consonants:
                current_cluster += 1
            else:
                if current_cluster >= 3:
                    cluster_count += 1
                max_cluster = max(max_cluster, current_cluster)
                current_cluster = 0
        
        # Final cluster
        if current_cluster >= 3:
            cluster_count += 1
        max_cluster = max(max_cluster, current_cluster)
        
        # Vietnamese rarely has 3+ consonant clusters, never 4+
        if max_cluster >= 4:
            logger.debug(f"Long consonant cluster ({max_cluster}) detected")
            return True
        
        # Multiple 3-consonant clusters is suspicious
        if cluster_count >= 2:
            logger.debug(f"Multiple consonant clusters ({cluster_count}) detected")
            return True
        
        # Pattern-based check for shorter strings
        common_patterns = [
            # Common Vietnamese syllables (romanized)
            "an", "en", "in", "on", "un", "ang", "eng", "ong",
            "ai", "ao", "au", "ay", "eo", "ia", "ie", "iu", "oa", "oe", "oi", "ou", "ua", "ue", "ui", "uo", "uy",
            "anh", "inh", "ung", "uong",
            # Common Vietnamese word endings
            "nh", "ng", "ch",
            # Common Vietnamese beginnings  
            "th", "tr", "kh", "ph",
        ]
        
        pattern_count = sum(1 for p in common_patterns if p in text_lower)
        
        # Pattern density: patterns per character
        # Vietnamese text typically has pattern density > 0.15
        # Random text has lower density
        pattern_density = pattern_count / len(text_lower) if text_lower else 0
        
        # If a 10+ char text has low pattern density + consonant cluster, likely gibberish
        if len(text_lower) >= 10 and pattern_density < 0.15 and max_cluster >= 3:
            return True
        
        # If a 10+ char text has only 1-2 patterns, likely gibberish
        if len(text_lower) >= 10 and pattern_count <= 2:
            return True
        
        # If a 7-9 char text has 0 common patterns, likely gibberish
        if len(text_lower) >= 7 and pattern_count == 0:
            return True
        
        return False
    
    def _has_vietnamese_diacritics(self, text: str) -> bool:
        """Check if text contains Vietnamese diacritics."""
        diacritics = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
        return any(c in diacritics for c in text.lower())
    
    def _looks_like_keyboard_mash(self, text: str) -> bool:
        """
        Detect keyboard mashing patterns.
        
        Characteristics of keyboard mash:
        - Mix of random letters without structure
        - Often repeated key patterns
        - No meaningful Vietnamese words
        """
        text_lower = text.lower().replace(" ", "")
        
        if len(text_lower) < 6:
            return False
        
        # Check for keyboard row patterns (qwerty, asdf, etc.)
        keyboard_rows = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
        for row in keyboard_rows:
            row_chars = set(row)
            text_chars = set(text_lower)
            # If >70% chars from one keyboard row, likely mashing
            overlap = len(text_chars & row_chars) / len(text_chars) if text_chars else 0
            if overlap > 0.7 and len(text_lower) > 5:
                return True
        
        # Check for alternating patterns that aren't repeated (unlike asdasd)
        # Count unique consecutive pairs
        pairs = set()
        for i in range(len(text_lower) - 1):
            pairs.add(text_lower[i:i+2])
        
        # High pair diversity with no Vietnamese characteristics = gibberish
        pair_diversity = len(pairs) / (len(text_lower) - 1) if len(text_lower) > 1 else 0
        
        # Random text has high pair diversity (each pair unique)
        # Normal text has lower diversity (common letter combinations)
        if pair_diversity > 0.8 and len(text_lower) > 8:
            vowel_ratio = self._calculate_vowel_ratio(text)
            if vowel_ratio < 0.25:  # Low vowels + high diversity = gibberish
                return True
        
        return False
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        freq = {}
        for char in text_lower:
            freq[char] = freq.get(char, 0) + 1
        
        length = len(text_lower)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy
    
    def _calculate_vowel_ratio(self, text: str) -> float:
        """Calculate ratio of vowels in text."""
        # Vietnamese vowels including diacritics
        vowels = set("aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵ")
        
        alpha_chars = [c for c in text.lower() if c.isalpha()]
        if not alpha_chars:
            return 0.0
        
        vowel_count = sum(1 for c in alpha_chars if c in vowels)
        return vowel_count / len(alpha_chars)
    
    def _has_repeated_nonsense(self, text: str) -> bool:
        """Check for repeated nonsense patterns like 'asdasd', 'qwqwqw'."""
        text_lower = text.lower().replace(" ", "")
        
        if len(text_lower) < 6:
            return False
        
        # Check for 2-3 char repeated patterns
        for pattern_len in [2, 3]:
            pattern = text_lower[:pattern_len]
            repeated = pattern * (len(text_lower) // pattern_len + 1)
            if text_lower in repeated:
                return True
        
        return False
    
    def _check_casual(self, query: str) -> Optional[IntentResult]:
        """Check if query matches casual patterns."""
        for category, patterns in self._casual_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    return IntentResult(
                        intent=QueryIntent.CASUAL,
                        confidence=0.9,
                        reason=f"Matched casual pattern: {category}",
                        suggested_response=self.CASUAL_RESPONSES.get(category),
                    )
        return None
    
    def _is_context_follow_up(self, query: str) -> bool:
        """Check if query references previous context."""
        return any(pattern.search(query) for pattern in self._context_patterns)
    
    def _calculate_domain_score(self, query: str) -> float:
        """Calculate domain relevance score based on keyword matching."""
        if not query:
            return 0.0
        
        words = query.split()
        if not words:
            return 0.0
        
        matched_keywords = 0
        for keyword in self.DOMAIN_KEYWORDS:
            if keyword in query:
                matched_keywords += 1
        
        # Normalize by query length (longer queries need more keywords)
        # But cap at certain thresholds
        word_count = len(words)
        if word_count <= 5:
            threshold = 1
        elif word_count <= 15:
            threshold = 2
        else:
            threshold = 3
        
        return min(matched_keywords / threshold, 1.0)
    
    def _has_question_pattern(self, query: str) -> bool:
        """Check if query has Vietnamese question patterns."""
        question_patterns = [
            r"\?$",  # Ends with ?
            r"^(ai|gì|đâu|khi\s+nào|bao\s+nhiêu|như\s+thế\s+nào|tại\s+sao|vì\s+sao)",
            r"(là\s+gì|như\s+thế\s+nào|ra\s+sao)",
            r"(có\s+thể|được\s+không|phải\s+không)",
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in question_patterns)


# Singleton instance
_intent_detector: Optional[IntentDetector] = None


def get_intent_detector() -> IntentDetector:
    """Get singleton IntentDetector instance."""
    global _intent_detector
    if _intent_detector is None:
        _intent_detector = IntentDetector()
    return _intent_detector


# Quick helper function
def detect_intent(query: str, context: Optional[str] = None) -> IntentResult:
    """Quick function to detect query intent."""
    return get_intent_detector().detect(query, context)
