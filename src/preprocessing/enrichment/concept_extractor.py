"""
Legal Concept Extractor - Extract legal concepts from Vietnamese legal text.

Extracts domain-specific legal concepts like:
- Bidding types (đấu thầu rộng rãi, đấu thầu hạn chế)
- Contract types (hợp đồng trọn gói, hợp đồng theo đơn giá)
- Procedures (thủ tục, quy trình)
- Legal terms (vi phạm, xử phạt, trách nhiệm)
"""

import re
from typing import List, Dict, Set
from dataclasses import dataclass


@dataclass
class LegalConcept:
    """Represents an extracted legal concept."""

    concept: str  # The concept text
    category: str  # 'bidding', 'contract', 'procedure', 'penalty', etc.
    frequency: int = 1  # How many times it appears
    confidence: float = 1.0


class LegalConceptExtractor:
    """Extract legal concepts from Vietnamese legal documents."""

    def __init__(self):
        self.concept_patterns = self._build_concept_patterns()

    def _build_concept_patterns(self) -> Dict[str, List[str]]:
        """Build concept patterns by category."""
        return {
            "bidding": [
                # Bidding types
                r"đấu thầu rộng rãi",
                r"đấu thầu hạn chế",
                r"đấu thầu qua mạng",
                r"chỉ định thầu",
                r"mua sắm trực tiếp",
                r"tự thực hiện",
                # Bidding stages
                r"mở thầu",
                r"đánh giá hồ sơ dự thầu",
                r"thẩm định kết quả",
                r"phê duyệt kết quả",
                r"ký kết hợp đồng",
                # Bidding documents
                r"hồ sơ mời thầu",
                r"hồ sơ dự thầu",
                r"bảo đảm dự thầu",
                r"bảo đảm thực hiện hợp đồng",
                r"E-HSDT",
            ],
            "contract": [
                # Contract types
                r"hợp đồng trọn gói",
                r"hợp đồng theo đơn giá",
                r"hợp đồng hỗn hợp",
                r"hợp đồng theo thời gian",
                # Contract terms
                r"giá trúng thầu",
                r"thời gian thực hiện",
                r"nghĩa vụ hợp đồng",
                r"thanh lý hợp đồng",
                r"bảo hành",
            ],
            "procedure": [
                r"thủ tục hành chính",
                r"quy trình phê duyệt",
                r"trình tự thực hiện",
                r"hồ sơ đề nghị",
                r"thẩm định",
                r"phê duyệt",
                r"công bố",
                r"thông báo",
            ],
            "penalty": [
                r"vi phạm",
                r"xử phạt",
                r"phạt tiền",
                r"đình chỉ",
                r"thu hồi",
                r"cấm tham gia",
                r"trách nhiệm",
                r"bồi thường",
            ],
            "authority": [
                r"thẩm quyền",
                r"phân cấp",
                r"ủy quyền",
                r"chủ đầu tư",
                r"bên mời thầu",
                r"nhà thầu",
                r"tổ chuyên gia",
            ],
            "planning": [
                r"kế hoạch đấu thầu",
                r"kế hoạch lựa chọn nhà thầu",
                r"dự án",
                r"gói thầu",
                r"dự toán",
                r"phân bổ vốn",
            ],
        }

    def extract(self, text: str) -> List[LegalConcept]:
        """
        Extract legal concepts from text.

        Args:
            text: Input text to analyze

        Returns:
            List of extracted concepts with frequencies
        """
        text_lower = text.lower()
        concepts = []
        found_concepts: Dict[str, Dict[str, any]] = {}

        for category, patterns in self.concept_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text_lower)
                count = sum(1 for _ in matches)

                if count > 0:
                    key = f"{category}:{pattern}"
                    if key not in found_concepts:
                        found_concepts[key] = {
                            "concept": pattern,
                            "category": category,
                            "frequency": count,
                        }

        # Convert to LegalConcept objects
        for data in found_concepts.values():
            concepts.append(
                LegalConcept(
                    concept=data["concept"],
                    category=data["category"],
                    frequency=data["frequency"],
                    confidence=1.0,
                )
            )

        # Sort by frequency (most common first)
        concepts.sort(key=lambda c: c.frequency, reverse=True)

        return concepts

    def extract_as_metadata(self, text: str, top_n: int = 10) -> Dict[str, any]:
        """
        Extract concepts and return as metadata.

        Args:
            text: Input text
            top_n: Maximum concepts to include per category

        Returns:
            Dict with concept categories and top concepts
        """
        concepts = self.extract(text)

        metadata = {
            "concepts": [],
            "concept_categories": set(),
            "primary_concepts": [],
        }

        # Group by category
        by_category: Dict[str, List[str]] = {}
        for concept in concepts:
            if concept.category not in by_category:
                by_category[concept.category] = []
            by_category[concept.category].append(concept.concept)
            metadata["concept_categories"].add(concept.category)

        # Take top N from each category
        for category, concept_list in by_category.items():
            metadata["concepts"].extend(concept_list[:top_n])

        # Primary concepts = top 5 overall
        metadata["primary_concepts"] = [c.concept for c in concepts[:5]]

        # Convert set to list for JSON serialization
        metadata["concept_categories"] = list(metadata["concept_categories"])

        return metadata

    def identify_document_focus(self, text: str) -> str:
        """
        Identify the primary focus/topic of the document.

        Returns:
            Category with most concepts (e.g., 'bidding', 'contract')
        """
        concepts = self.extract(text)

        if not concepts:
            return "general"

        # Count concepts by category
        category_counts: Dict[str, int] = {}
        for concept in concepts:
            category_counts[concept.category] = (
                category_counts.get(concept.category, 0) + concept.frequency
            )

        # Return category with highest count
        if category_counts:
            return max(category_counts.items(), key=lambda x: x[1])[0]

        return "general"
