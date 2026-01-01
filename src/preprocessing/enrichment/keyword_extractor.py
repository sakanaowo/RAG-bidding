"""
Keyword Extractor - Extract important keywords using TF-IDF approach.

For Vietnamese legal text, extracts:
- High-frequency legal terms
- Important noun phrases
- Section-specific keywords
"""

import re
from typing import List, Dict, Tuple
from collections import Counter
from dataclasses import dataclass
import math


@dataclass
class Keyword:
    """Represents an extracted keyword."""

    term: str
    score: float  # TF-IDF or frequency-based score
    category: str = "general"  # 'legal_term', 'noun_phrase', 'general'


class KeywordExtractor:
    """Extract keywords from Vietnamese legal text using TF-IDF-like approach."""

    def __init__(self):
        # Common Vietnamese stopwords
        self.stopwords = self._build_stopwords()

        # Legal-specific important terms (boost these)
        self.legal_terms = self._build_legal_terms()

    def _build_stopwords(self) -> set:
        """Build Vietnamese stopwords list."""
        return {
            # Pronouns
            "của",
            "và",
            "các",
            "có",
            "được",
            "cho",
            "từ",
            "trong",
            "là",
            "với",
            "để",
            "về",
            "theo",
            "tại",
            "do",
            "bởi",
            "khi",
            "này",
            "đó",
            "những",
            "như",
            "đã",
            "sẽ",
            "hoặc",
            "nếu",
            "mà",
            "kể",
            "hay",
            "được",
            "bị",
            # Articles
            "một",
            "các",
            "những",
            "mỗi",
            # Common verbs (low information)
            "phải",
            "cần",
            "nên",
            "thể",
            "bao gồm",
            "gồm",
        }

    def _build_legal_terms(self) -> set:
        """Build important legal terms that should be boosted."""
        return {
            # Legal documents
            "luật",
            "nghị định",
            "thông tư",
            "quyết định",
            "quy định",
            "pháp luật",
            "văn bản",
            "quy chế",
            "điều lệ",
            # Bidding terms
            "đấu thầu",
            "nhà thầu",
            "thầu",
            "gói thầu",
            "dự thầu",
            "mời thầu",
            "trúng thầu",
            "kết quả",
            "hồ sơ",
            # Contract terms
            "hợp đồng",
            "ký kết",
            "thực hiện",
            "nghĩa vụ",
            "quyền",
            # Administrative
            "thẩm quyền",
            "phê duyệt",
            "phân cấp",
            "ủy quyền",
            "thủ tục",
            "quy trình",
            "trình tự",
            # Penalties
            "vi phạm",
            "xử phạt",
            "trách nhiệm",
            "bồi thường",
        }

    def extract(self, text: str, top_n: int = 20) -> List[Keyword]:
        """
        Extract top N keywords from text.

        Args:
            text: Input text
            top_n: Number of keywords to extract

        Returns:
            List of keywords sorted by score
        """
        # Tokenize (simple word-based for Vietnamese)
        tokens = self._tokenize(text)

        # Calculate term frequencies
        term_freq = Counter(tokens)

        # Calculate scores
        keywords = []
        max_freq = max(term_freq.values()) if term_freq else 1

        for term, freq in term_freq.items():
            # Skip stopwords
            if term.lower() in self.stopwords:
                continue

            # Skip single characters
            if len(term) <= 1:
                continue

            # Calculate normalized TF
            tf_score = freq / max_freq

            # Boost legal terms
            boost = 1.5 if term.lower() in self.legal_terms else 1.0

            # Category classification
            category = "legal_term" if term.lower() in self.legal_terms else "general"

            # Final score
            score = tf_score * boost

            keywords.append(Keyword(term=term, score=score, category=category))

        # Sort by score
        keywords.sort(key=lambda k: k.score, reverse=True)

        return keywords[:top_n]

    def _tokenize(self, text: str) -> List[str]:
        """
        Simple tokenization for Vietnamese.

        Extracts:
        - Multi-word legal phrases (e.g., "đấu thầu rộng rãi")
        - Compound words (e.g., "hợp_đồng")
        - Single words
        """
        tokens = []

        # First, extract multi-word legal phrases
        multi_word_patterns = [
            r"đấu thầu (?:rộng rãi|hạn chế|qua mạng)",
            r"hợp đồng (?:trọn gói|theo đơn giá|hỗn hợp)",
            r"hồ sơ (?:mời thầu|dự thầu|đề nghị)",
            r"bảo đảm (?:dự thầu|thực hiện hợp đồng)",
            r"kế hoạch (?:đấu thầu|lựa chọn nhà thầu)",
            r"thủ tục hành chính",
            r"chỉ định thầu",
            r"mua sắm trực tiếp",
            r"xử lý vi phạm",
        ]

        text_remaining = text.lower()
        for pattern in multi_word_patterns:
            for match in re.finditer(pattern, text_remaining):
                phrase = match.group(0)
                tokens.append(phrase)
                # Remove matched phrase to avoid double-counting
                text_remaining = text_remaining.replace(phrase, " ", 1)

        # Then extract individual words (Vietnamese + numbers)
        word_pattern = r"[a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]+|\d+"
        words = re.findall(word_pattern, text_remaining, re.IGNORECASE)
        tokens.extend(words)

        return tokens

    def extract_as_metadata(self, text: str, top_n: int = 15) -> Dict[str, any]:
        """
        Extract keywords and return as metadata.

        Returns:
            Dict with keywords, legal_terms, and general_terms
        """
        keywords = self.extract(text, top_n=top_n)

        metadata = {
            "keywords": [k.term for k in keywords],
            "legal_terms": [k.term for k in keywords if k.category == "legal_term"],
            "keyword_count": len(keywords),
        }

        return metadata

    def extract_bigrams(self, text: str, top_n: int = 10) -> List[Tuple[str, int]]:
        """
        Extract most common bigrams (2-word phrases).

        Useful for finding common legal phrases.
        """
        tokens = self._tokenize(text)

        # Filter out stopwords
        tokens = [t for t in tokens if t.lower() not in self.stopwords and len(t) > 1]

        # Create bigrams
        bigrams = []
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            bigrams.append(bigram)

        # Count frequencies
        bigram_freq = Counter(bigrams)

        # Return top N
        return bigram_freq.most_common(top_n)
