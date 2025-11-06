"""
Document Type Classifier
Automatic classification of Vietnamese legal and bidding documents
"""

import re
from typing import Tuple, List, Dict
from pathlib import Path
import logging

from ..schemas.upload_schemas import DocumentType

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Automatic document type classification based on content and filename analysis.

    Uses rule-based approach with keyword matching and pattern recognition
    for Vietnamese legal and bidding documents.
    """

    def __init__(self):
        self.classification_rules = self._setup_classification_rules()

    def _setup_classification_rules(self) -> Dict[DocumentType, Dict]:
        """Setup classification rules for each document type"""
        return {
            DocumentType.LAW: {
                "filename_patterns": [
                    r"luật.*\d{4}",
                    r"law.*\d{4}",
                    r"^luat",
                    r"qh\d+.*luat",
                    r"quốc hội.*luật",
                ],
                "content_keywords": [
                    "quốc hội",
                    "luật số",
                    "có hiệu lực",
                    "điều khoản",
                    "chương",
                    "mục",
                    "phần",
                    "ban hành",
                ],
                "legal_patterns": [
                    r"luật số \d+/\d+/qh\d+",
                    r"điều \d+",
                    r"khoản \d+",
                    r"chương [ivxlcdm]+",
                    r"phần thứ [ivxlcdm]+",
                ],
                "authority_indicators": ["quốc hội", "chủ tịch nước"],
                "confidence_weight": 0.9,
            },
            DocumentType.DECREE: {
                "filename_patterns": [
                    r"nghị định",
                    r"nghi dinh",
                    r"decree",
                    r"nd.*\d+",
                    r"^nd-",
                    r"n\.d",
                ],
                "content_keywords": [
                    "nghị định",
                    "thủ tướng",
                    "chính phủ",
                    "quy định chi tiết",
                    "hướng dẫn thi hành",
                ],
                "legal_patterns": [
                    r"nghị định số \d+/\d+/nd-cp",
                    r"điều \d+",
                    r"khoản \d+",
                    r"chương [ivxlcdm]+",
                ],
                "authority_indicators": ["thủ tướng chính phủ", "chính phủ"],
                "confidence_weight": 0.85,
            },
            DocumentType.CIRCULAR: {
                "filename_patterns": [
                    r"thông tư",
                    r"thong tu",
                    r"circular",
                    r"tt.*\d+",
                    r"^tt-",
                    r"t\.t",
                ],
                "content_keywords": [
                    "thông tư",
                    "bộ trường",
                    "hướng dẫn",
                    "quy định",
                    "thi hành",
                    "áp dụng",
                ],
                "legal_patterns": [
                    r"thông tư số \d+/\d+/tt-",
                    r"điều \d+",
                    r"khoản \d+",
                ],
                "authority_indicators": ["bộ", "ủy ban", "tổng cục"],
                "confidence_weight": 0.8,
            },
            DocumentType.DECISION: {
                "filename_patterns": [
                    r"quyết định",
                    r"quyet dinh",
                    r"decision",
                    r"qd.*\d+",
                    r"^qd-",
                    r"q\.d",
                ],
                "content_keywords": [
                    "quyết định",
                    "ban hành",
                    "phê duyệt",
                    "công bố",
                    "có hiệu lực",
                ],
                "legal_patterns": [
                    r"quyết định số \d+/\d+/qd-",
                    r"điều \d+",
                    r"khoản \d+",
                ],
                "authority_indicators": ["thủ tướng", "bộ trường", "chủ tịch"],
                "confidence_weight": 0.75,
            },
            DocumentType.BIDDING: {
                "filename_patterns": [
                    r"hồ sơ.*thầu",
                    r"ho so.*thau",
                    r"mời thầu",
                    r"moi thau",
                    r"tender",
                    r"bidding",
                    r"hsmt",
                    r"e-bidding",
                ],
                "content_keywords": [
                    "mời thầu",
                    "hồ sơ mời thầu",
                    "nhà thầu",
                    "gói thầu",
                    "đấu thầu",
                    "dự thầu",
                    "tham gia thầu",
                    "kế hoạch lựa chọn",
                ],
                "legal_patterns": [
                    r"gói thầu số",
                    r"hsmt.*\d+",
                    r"kế hoạch lựa chọn nhà thầu",
                    r"giá trị gói thầu",
                ],
                "authority_indicators": ["chủ đầu tư", "bên mời thầu"],
                "confidence_weight": 0.85,
            },
            DocumentType.REPORT: {
                "filename_patterns": [
                    r"mẫu.*báo cáo",
                    r"mau.*bao cao",
                    r"template",
                    r"form",
                    r"báo cáo",
                    r"bao cao",
                    r"report",
                ],
                "content_keywords": [
                    "báo cáo",
                    "mẫu",
                    "template",
                    "biểu mẫu",
                    "form",
                    "định dạng",
                    "hướng dẫn",
                    "điền",
                ],
                "legal_patterns": [r"mẫu số \d+", r"biểu mẫu.*\d+", r"báo cáo.*năm"],
                "authority_indicators": ["ban", "sở", "phòng", "cục"],
                "confidence_weight": 0.7,
            },
            DocumentType.EXAM: {
                "filename_patterns": [
                    r"câu hỏi.*thi",
                    r"cau hoi.*thi",
                    r"đề thi",
                    r"de thi",
                    r"test",
                    r"exam",
                    r"quiz",
                    r"question",
                ],
                "content_keywords": [
                    "câu hỏi",
                    "đề thi",
                    "bài thi",
                    "kiểm tra",
                    "đáp án",
                    "lựa chọn",
                    "trắc nghiệm",
                    "tự luận",
                ],
                "legal_patterns": [r"câu \d+", r"đáp án [abcd]", r"phương án"],
                "authority_indicators": ["trường", "viện", "trung tâm"],
                "confidence_weight": 0.8,
            },
        }

    def classify_document(
        self, filename: str, content: str = None
    ) -> Tuple[DocumentType, float, str]:
        """
        Classify document based on filename and content.

        Args:
            filename: Original filename
            content: Document text content (optional)

        Returns:
            Tuple of (document_type, confidence, reasoning)
        """
        try:
            scores = {}
            reasoning_parts = []

            # Clean inputs
            clean_filename = self._normalize_vietnamese_text(filename.lower())
            clean_content = (
                self._normalize_vietnamese_text(content.lower()) if content else ""
            )

            # Score each document type
            for doc_type, rules in self.classification_rules.items():
                score = 0.0
                matches = []

                # Check filename patterns
                filename_score = self._check_filename_patterns(
                    clean_filename, rules["filename_patterns"]
                )
                if filename_score > 0:
                    score += filename_score * 0.4  # 40% weight for filename
                    matches.append(f"filename patterns")

                # Check content keywords (if content available)
                if clean_content:
                    content_score = self._check_content_keywords(
                        clean_content, rules["content_keywords"]
                    )
                    if content_score > 0:
                        score += content_score * 0.3  # 30% weight for content keywords
                        matches.append(f"content keywords")

                    # Check legal patterns
                    legal_score = self._check_legal_patterns(
                        clean_content, rules["legal_patterns"]
                    )
                    if legal_score > 0:
                        score += legal_score * 0.2  # 20% weight for legal patterns
                        matches.append(f"legal patterns")

                    # Check authority indicators
                    authority_score = self._check_authority_indicators(
                        clean_content, rules["authority_indicators"]
                    )
                    if authority_score > 0:
                        score += authority_score * 0.1  # 10% weight for authority
                        matches.append(f"authority indicators")

                # Apply confidence weight
                final_score = score * rules["confidence_weight"]
                scores[doc_type] = final_score

                if matches:
                    reasoning_parts.append(
                        f"{doc_type.value}: {', '.join(matches)} (score: {final_score:.2f})"
                    )

            # Find best match
            if not scores or max(scores.values()) == 0:
                return DocumentType.OTHER, 0.1, "No clear patterns detected"

            best_type = max(scores.keys(), key=lambda x: scores[x])
            confidence = min(scores[best_type], 1.0)  # Cap at 1.0

            reasoning = (
                f"Best match: {best_type.value} (confidence: {confidence:.2f}). "
                + f"Analysis: {'; '.join(reasoning_parts)}"
            )

            logger.info(
                f"Classified '{filename}' as {best_type.value} with confidence {confidence:.2f}"
            )
            return best_type, confidence, reasoning

        except Exception as e:
            logger.error(f"Classification error for '{filename}': {str(e)}")
            return DocumentType.OTHER, 0.1, f"Classification failed: {str(e)}"

    def _normalize_vietnamese_text(self, text: str) -> str:
        """Normalize Vietnamese text for better matching"""
        if not text:
            return ""

        # Remove diacritics mapping
        vietnamese_map = {
            "à": "a",
            "á": "a",
            "ả": "a",
            "ã": "a",
            "ạ": "a",
            "ă": "a",
            "ằ": "a",
            "ắ": "a",
            "ẳ": "a",
            "ẵ": "a",
            "ặ": "a",
            "â": "a",
            "ầ": "a",
            "ấ": "a",
            "ẩ": "a",
            "ẫ": "a",
            "ậ": "a",
            "è": "e",
            "é": "e",
            "ẻ": "e",
            "ẽ": "e",
            "ẹ": "e",
            "ê": "e",
            "ề": "e",
            "ế": "e",
            "ể": "e",
            "ễ": "e",
            "ệ": "e",
            "ì": "i",
            "í": "i",
            "ỉ": "i",
            "ĩ": "i",
            "ị": "i",
            "ò": "o",
            "ó": "o",
            "ỏ": "o",
            "õ": "o",
            "ọ": "o",
            "ô": "o",
            "ồ": "o",
            "ố": "o",
            "ổ": "o",
            "ỗ": "o",
            "ộ": "o",
            "ơ": "o",
            "ờ": "o",
            "ớ": "o",
            "ở": "o",
            "ỡ": "o",
            "ợ": "o",
            "ù": "u",
            "ú": "u",
            "ủ": "u",
            "ũ": "u",
            "ụ": "u",
            "ư": "u",
            "ừ": "u",
            "ứ": "u",
            "ử": "u",
            "ữ": "u",
            "ự": "u",
            "ỳ": "y",
            "ý": "y",
            "ỷ": "y",
            "ỹ": "y",
            "ỵ": "y",
            "đ": "d",
        }

        normalized = text.lower()
        for vn_char, latin_char in vietnamese_map.items():
            normalized = normalized.replace(vn_char, latin_char)

        return normalized

    def _check_filename_patterns(self, filename: str, patterns: List[str]) -> float:
        """Check filename against patterns"""
        matches = sum(1 for pattern in patterns if re.search(pattern, filename))
        return min(matches / len(patterns), 1.0) if patterns else 0.0

    def _check_content_keywords(self, content: str, keywords: List[str]) -> float:
        """Check content for keywords"""
        if not content or not keywords:
            return 0.0

        matches = sum(1 for keyword in keywords if keyword in content)
        return min(matches / len(keywords), 1.0)

    def _check_legal_patterns(self, content: str, patterns: List[str]) -> float:
        """Check content for legal patterns"""
        if not content or not patterns:
            return 0.0

        matches = sum(1 for pattern in patterns if re.search(pattern, content))
        return min(matches / len(patterns), 1.0)

    def _check_authority_indicators(self, content: str, indicators: List[str]) -> float:
        """Check content for authority indicators"""
        if not content or not indicators:
            return 0.0

        matches = sum(1 for indicator in indicators if indicator in content)
        return min(matches / len(indicators), 1.0)

    def get_features_detected(self, filename: str, content: str = None) -> List[str]:
        """Get list of detected features for transparency"""
        features = []

        clean_filename = self._normalize_vietnamese_text(filename.lower())
        clean_content = (
            self._normalize_vietnamese_text(content.lower()) if content else ""
        )

        # Check for common features
        if re.search(r"\d{4}", clean_filename):
            features.append("year_in_filename")

        if clean_content:
            if re.search(r"điều \d+", clean_content):
                features.append("article_structure")
            if re.search(r"chương [ivxlcdm]+", clean_content):
                features.append("chapter_structure")
            if any(
                auth in clean_content for auth in ["quốc hội", "chính phủ", "thủ tướng"]
            ):
                features.append("government_authority")
            if re.search(r"số \d+/\d+", clean_content):
                features.append("document_number_format")

        return features
