"""
Decree Cleaner - Clean decree text

Reuse legal cleaning patterns từ law_preprocessing
"""

from typing import List
import re

# Reuse legal cleaner từ law module
from ...law_preprocessing.cleaners.legal_cleaner import LegalDocumentCleaner


class DecreeCleaner(LegalDocumentCleaner):
    """
    Cleaner cho Nghị định
    
    Kế thừa từ LegalCleaner nhưng có thể add decree-specific rules
    """

    def __init__(self):
        """Initialize với legal patterns"""
        super().__init__()
        
        # Add decree-specific patterns if needed
        self.decree_patterns = {
            # Remove "Nghị định số..." headers (duplicate info)
            "decree_header": re.compile(
                r"^Nghị định số\s+\d+/\d{4}/NĐ-CP.*$",
                re.MULTILINE
            ),
            # Remove government signature blocks
            "gov_signature": re.compile(
                r"(CHỦ TỊCH NỘI DUNG|THỦ TƯỚNG|Nơi nhận:).*",
                re.DOTALL
            ),
        }
        
        print("✅ DecreeCleaner initialized")

    def clean(self, text: str) -> str:
        """
        Clean decree text
        
        Args:
            text: Raw decree text
            
        Returns:
            Cleaned text
        """
        # Use parent's legal cleaning
        cleaned = super().clean(text)
        
        # Apply decree-specific cleaning
        for pattern_name, pattern in self.decree_patterns.items():
            cleaned = pattern.sub("", cleaned)
        
        return cleaned.strip()

    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        Clean multiple texts
        
        Args:
            texts: List of texts
            
        Returns:
            List of cleaned texts
        """
        return [self.clean(text) for text in texts]
