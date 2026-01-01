"""
Base Cleaner - Abstract class cho text cleaning
"""

from abc import ABC, abstractmethod


class BaseCleaner(ABC):
    """
    Abstract base class cho text cleaners
    """

    @abstractmethod
    def clean(self, text: str) -> str:
        """
        Clean and normalize text

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text

        Raises:
            ValueError: Invalid text
        """
        pass

    @abstractmethod
    def get_cleaning_stats(self, original: str, cleaned: str) -> dict:
        """
        Get statistics về cleaning process

        Args:
            original: Original text
            cleaned: Cleaned text

        Returns:
            Dictionary with stats (chars removed, normalized, etc.)
        """
        pass
