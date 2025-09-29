import re
import logging
from typing import Callable, Optional
import unicodedata

logger = logging.getLogger(__name__)

WS = re.compile(r"[\t\f\r]+")
MULTIPLE_SPACES = re.compile(r" {2,}")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
URL_PATTERN = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)
PHONE_PATTERN = re.compile(r"(\+?84|0)[1-9]\d{8,9}")


def basic_clean(text: str) -> str:
    """Basic text cleaning for removing unwanted whitespace and characters."""
    if not text or not isinstance(text, str):
        return ""

    try:
        # Replace non-breaking spaces
        text = text.replace("\u00a0", " ")
        text = text.replace("\r", "\n").replace("\t", " ")

        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Clean whitespace
        text = WS.sub(" ", text)
        text = MULTIPLE_SPACES.sub(" ", text)
        text = text.strip()

        return text
    except Exception as e:
        logger.warning(f"Error in basic_clean: {e}")
        return text


def advanced_clean(
    text: str,
    remove_emails: bool = False,
    remove_urls: bool = False,
    remove_phone: bool = False,
) -> str:
    """Advanced text cleaning with optional PII removal."""
    if not text or not isinstance(text, str):
        return ""

    try:
        # Start with basic cleaning
        text = basic_clean(text)

        # Normalize unicode characters
        text = unicodedata.normalize("NFKC", text)

        # Remove or mask sensitive information if requested
        if remove_emails:
            text = EMAIL_PATTERN.sub("[EMAIL]", text)
        if remove_urls:
            text = URL_PATTERN.sub("[URL]", text)
        if remove_phone:
            text = PHONE_PATTERN.sub("[PHONE]", text)

        # Remove excessive punctuation
        text = re.sub(r"[.]{3,}", "...", text)
        text = re.sub(r"[!]{2,}", "!", text)
        text = re.sub(r"[?]{2,}", "?", text)

        # Remove bullet points and list markers at start of lines
        text = re.sub(r"^[\s]*[•◦▪▫-]\s*", "", text, flags=re.MULTILINE)

        # Remove page numbers and headers/footers patterns
        text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
        text = re.sub(r"\n\s*Page\s+\d+.*?\n", "\n", text, flags=re.IGNORECASE)

        return text.strip()

    except Exception as e:
        logger.warning(f"Error in advanced_clean: {e}")
        return basic_clean(text)


def vietnamese_specific_clean(text: str) -> str:
    """Specific cleaning for Vietnamese text."""
    if not text or not isinstance(text, str):
        return ""

    try:
        # Start with advanced cleaning
        text = advanced_clean(text)

        # Fix common Vietnamese encoding issues
        vietnamese_replacements = {
            "Ä‚": "Â",
            "Trang": "",  # Remove page numbers
            "TRANG": "",  # Remove page numbers uppercase
        }

        for wrong, correct in vietnamese_replacements.items():
            text = text.replace(wrong, correct)

        # Remove common Vietnamese document artifacts
        text = re.sub(r"Trang\s+\d+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"Chương\s+[IVX\d]+\s*:", "Chương:", text, flags=re.IGNORECASE)

        return text.strip()

    except Exception as e:
        logger.warning(f"Error in vietnamese_specific_clean: {e}")
        return advanced_clean(text)


def validate_cleaned_text(text: str, min_length: int = 10) -> bool:
    """Validate that cleaned text meets quality standards."""
    if not text or not isinstance(text, str):
        return False

    # Check minimum length
    if len(text.strip()) < min_length:
        return False

    # Check if text is mostly meaningful (not just numbers/symbols)
    meaningful_chars = len(re.sub(r"[^\w\s]", "", text, flags=re.UNICODE))
    total_chars = len(text)

    if total_chars == 0:
        return False

    meaningful_ratio = meaningful_chars / total_chars

    # At least 70% should be meaningful characters
    return meaningful_ratio >= 0.7


Cleaner = Callable[[str], str]
