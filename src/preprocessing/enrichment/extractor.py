"""
Legal Entity Extractor (NER) - Extract legal entities from Vietnamese legal text.

Extracts:
- Laws (Luật, Bộ luật)
- Decrees (Nghị định)
- Circulars (Thông tư)
- Decisions (Quyết định)
- Dates (effective dates, signing dates)
- Organizations (Ministries, agencies)
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class LegalEntity:
    """Represents an extracted legal entity."""

    entity_type: str  # 'law', 'decree', 'circular', 'decision', 'date', 'organization'
    text: str  # Original text
    normalized: str  # Normalized form
    position: Tuple[int, int]  # (start, end) in text
    confidence: float = 1.0


class LegalEntityExtractor:
    """Extract legal entities from Vietnamese legal documents."""

    def __init__(self):
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for entity extraction."""
        return {
            # Laws - Luật 10/2023/QH15
            "law": re.compile(
                r"(?:Luật|Bộ luật)\s+(?:số\s+)?(\d+[A-Z]*(?:/\d{4}(?:/[A-Z0-9]+)?)?)",
                re.IGNORECASE,
            ),
            # Decrees - Nghị định 10/2024/NĐ-CP
            "decree": re.compile(
                r"Nghị định\s+(?:số\s+)?(\d+[A-Z]*(?:/\d{4}(?:/[A-Z\-]+)?)?)",
                re.IGNORECASE,
            ),
            # Circulars - Thông tư 10/2024/TT-BTC
            "circular": re.compile(
                r"Thông tư\s+(?:số\s+)?(\d+[A-Z]*(?:/\d{4}(?:/[A-Z\-]+)?)?)",
                re.IGNORECASE,
            ),
            # Decisions - Quyết định 10/2024/QĐ-TTg
            "decision": re.compile(
                r"Quyết định\s+(?:số\s+)?(\d+[A-Z]*(?:/\d{4}(?:/[A-Z\-]+)?)?)",
                re.IGNORECASE,
            ),
            # Dates - 01/01/2024, ngày 01 tháng 01 năm 2024
            "date_numeric": re.compile(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})"),
            "date_text": re.compile(
                r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE
            ),
            # Organizations - Bộ Tài chính, Chính phủ
            "ministry": re.compile(
                r"Bộ\s+([A-ZÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ][a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ\s]+)",
                re.IGNORECASE,
            ),
            "government": re.compile(
                r"(Chính phủ|Thủ tướng Chính phủ|Quốc hội)", re.IGNORECASE
            ),
        }

    def extract(self, text: str) -> List[LegalEntity]:
        """
        Extract all legal entities from text.

        Args:
            text: Input text to extract from

        Returns:
            List of extracted entities
        """
        entities = []

        # Extract laws
        for match in self.patterns["law"].finditer(text):
            entities.append(
                LegalEntity(
                    entity_type="law",
                    text=match.group(0),
                    normalized=f"Luật {match.group(1)}",
                    position=(match.start(), match.end()),
                    confidence=1.0,
                )
            )

        # Extract decrees
        for match in self.patterns["decree"].finditer(text):
            entities.append(
                LegalEntity(
                    entity_type="decree",
                    text=match.group(0),
                    normalized=f"NĐ {match.group(1)}",
                    position=(match.start(), match.end()),
                    confidence=1.0,
                )
            )

        # Extract circulars
        for match in self.patterns["circular"].finditer(text):
            entities.append(
                LegalEntity(
                    entity_type="circular",
                    text=match.group(0),
                    normalized=f"TT {match.group(1)}",
                    position=(match.start(), match.end()),
                    confidence=1.0,
                )
            )

        # Extract decisions
        for match in self.patterns["decision"].finditer(text):
            entities.append(
                LegalEntity(
                    entity_type="decision",
                    text=match.group(0),
                    normalized=f"QĐ {match.group(1)}",
                    position=(match.start(), match.end()),
                    confidence=1.0,
                )
            )

        # Extract dates (numeric format)
        for match in self.patterns["date_numeric"].finditer(text):
            normalized_date = self._normalize_date(match.group(1))
            entities.append(
                LegalEntity(
                    entity_type="date",
                    text=match.group(0),
                    normalized=normalized_date,
                    position=(match.start(), match.end()),
                    confidence=0.9,
                )
            )

        # Extract dates (text format)
        for match in self.patterns["date_text"].finditer(text):
            day, month, year = match.groups()
            normalized_date = f"{day.zfill(2)}/{month.zfill(2)}/{year}"
            entities.append(
                LegalEntity(
                    entity_type="date",
                    text=match.group(0),
                    normalized=normalized_date,
                    position=(match.start(), match.end()),
                    confidence=1.0,
                )
            )

        # Extract ministries
        for match in self.patterns["ministry"].finditer(text):
            entities.append(
                LegalEntity(
                    entity_type="organization",
                    text=match.group(0),
                    normalized=match.group(0),
                    position=(match.start(), match.end()),
                    confidence=0.85,
                )
            )

        # Extract government entities
        for match in self.patterns["government"].finditer(text):
            entities.append(
                LegalEntity(
                    entity_type="organization",
                    text=match.group(0),
                    normalized=match.group(1),
                    position=(match.start(), match.end()),
                    confidence=1.0,
                )
            )

        # Sort by position
        entities.sort(key=lambda e: e.position[0])

        return entities

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to DD/MM/YYYY format."""
        # Handle both / and - separators
        parts = re.split(r"[\/\-]", date_str)
        if len(parts) == 3:
            day, month, year = parts
            return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
        return date_str

    def extract_as_metadata(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities and return as metadata dictionary.

        Returns:
            Dict with entity types as keys and lists of normalized entities
        """
        entities = self.extract(text)

        metadata = {
            "laws": [],
            "decrees": [],
            "circulars": [],
            "decisions": [],
            "dates": [],
            "organizations": [],
        }

        for entity in entities:
            if entity.entity_type == "law":
                metadata["laws"].append(entity.normalized)
            elif entity.entity_type == "decree":
                metadata["decrees"].append(entity.normalized)
            elif entity.entity_type == "circular":
                metadata["circulars"].append(entity.normalized)
            elif entity.entity_type == "decision":
                metadata["decisions"].append(entity.normalized)
            elif entity.entity_type == "date":
                metadata["dates"].append(entity.normalized)
            elif entity.entity_type == "organization":
                metadata["organizations"].append(entity.normalized)

        # Deduplicate
        for key in metadata:
            metadata[key] = list(set(metadata[key]))

        return metadata
