"""Data validation utilities for document processing pipeline."""

import logging
import hashlib
import re
from typing import List, Dict, Set, Optional, Tuple
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Validates documents for quality and content standards."""

    def __init__(
        self,
        min_length: int = 50,
        max_length: int = 50000,
        min_meaningful_ratio: float = 0.6,
        forbidden_patterns: Optional[List[str]] = None,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.min_meaningful_ratio = min_meaningful_ratio
        self.forbidden_patterns = forbidden_patterns or []

        # Compile forbidden patterns
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.forbidden_patterns
        ]

    def validate_document(self, doc: Document) -> Tuple[bool, List[str]]:
        """
        Validate a document and return validation result with reasons.

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []

        if not doc or not doc.page_content:
            issues.append("Document or content is empty")
            return False, issues

        content = doc.page_content.strip()

        # Check length constraints
        if len(content) < self.min_length:
            issues.append(f"Content too short: {len(content)} < {self.min_length}")

        if len(content) > self.max_length:
            issues.append(f"Content too long: {len(content)} > {self.max_length}")

        # Check meaningful content ratio
        meaningful_chars = len(re.sub(r"[^\w\s]", "", content, flags=re.UNICODE))
        if len(content) > 0:
            meaningful_ratio = meaningful_chars / len(content)
            if meaningful_ratio < self.min_meaningful_ratio:
                issues.append(
                    f"Low meaningful content ratio: {meaningful_ratio:.2f} < {self.min_meaningful_ratio}"
                )

        # Check for forbidden patterns
        for pattern in self.compiled_patterns:
            if pattern.search(content):
                issues.append(f"Contains forbidden pattern: {pattern.pattern}")

        # Check if content is mostly repeated characters
        unique_chars = len(set(content.lower()))
        if unique_chars < 10 and len(content) > 100:
            issues.append("Content appears to be mostly repeated characters")

        is_valid = len(issues) == 0

        if not is_valid:
            logger.warning(f"Document validation failed: {'; '.join(issues)}")

        return is_valid, issues

    def validate_documents(
        self, docs: List[Document]
    ) -> Tuple[List[Document], List[Document], Dict]:
        """
        Validate a list of documents.

        Returns:
            Tuple containing (valid_docs, invalid_docs, validation_stats)
        """
        valid_docs = []
        invalid_docs = []
        stats = {
            "total_docs": len(docs),
            "valid_docs": 0,
            "invalid_docs": 0,
            "issues_summary": {},
        }

        for doc in docs:
            is_valid, issues = self.validate_document(doc)

            if is_valid:
                valid_docs.append(doc)
                stats["valid_docs"] += 1
            else:
                invalid_docs.append(doc)
                stats["invalid_docs"] += 1

                # Track issue types
                for issue in issues:
                    issue_type = issue.split(":")[0]
                    stats["issues_summary"][issue_type] = (
                        stats["issues_summary"].get(issue_type, 0) + 1
                    )

        logger.info(
            f"Validation completed: {stats['valid_docs']}/{stats['total_docs']} documents passed validation"
        )

        return valid_docs, invalid_docs, stats


class DocumentDeduplicator:
    """Handles document deduplication based on content similarity."""

    def __init__(self, similarity_threshold: float = 0.95):
        self.similarity_threshold = similarity_threshold
        self.seen_hashes: Set[str] = set()
        self.content_map: Dict[str, Document] = {}

    def get_content_hash(self, content: str) -> str:
        """Generate a hash for document content."""
        normalized_content = re.sub(r"\s+", " ", content.lower().strip())
        return hashlib.md5(normalized_content.encode("utf-8")).hexdigest()

    def get_fuzzy_hash(self, content: str, chunk_size: int = 100) -> str:
        """Generate a fuzzy hash for near-duplicate detection."""
        # Create chunks and hash them
        words = content.lower().split()
        chunks = []

        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i + chunk_size])
            chunks.append(hashlib.md5(chunk.encode("utf-8")).hexdigest()[:8])

        return "".join(chunks)

    def is_duplicate(self, doc: Document) -> Tuple[bool, Optional[str]]:
        """
        Check if document is a duplicate.

        Returns:
            Tuple[bool, Optional[str]]: (is_duplicate, duplicate_hash_if_found)
        """
        content = doc.page_content
        content_hash = self.get_content_hash(content)

        # Exact duplicate check
        if content_hash in self.seen_hashes:
            return True, content_hash

        # Fuzzy duplicate check (for near-duplicates)
        fuzzy_hash = self.get_fuzzy_hash(content)
        for existing_hash, existing_doc in self.content_map.items():
            existing_fuzzy = self.get_fuzzy_hash(existing_doc.page_content)

            # Simple similarity check based on fuzzy hash
            common_chunks = sum(
                1
                for i in range(0, min(len(fuzzy_hash), len(existing_fuzzy)), 8)
                if fuzzy_hash[i : i + 8] == existing_fuzzy[i : i + 8]
            )

            total_chunks = max(len(fuzzy_hash), len(existing_fuzzy)) // 8
            if total_chunks > 0:
                similarity = common_chunks / total_chunks
                if similarity >= self.similarity_threshold:
                    return True, existing_hash

        return False, None

    def add_document(self, doc: Document) -> str:
        """Add document to deduplication tracking."""
        content_hash = self.get_content_hash(doc.page_content)
        self.seen_hashes.add(content_hash)
        self.content_map[content_hash] = doc
        return content_hash

    def deduplicate_documents(
        self, docs: List[Document]
    ) -> Tuple[List[Document], List[Document], Dict]:
        """
        Remove duplicates from document list.

        Returns:
            Tuple containing (unique_docs, duplicate_docs, deduplication_stats)
        """
        unique_docs = []
        duplicate_docs = []
        stats = {
            "total_docs": len(docs),
            "unique_docs": 0,
            "duplicate_docs": 0,
            "exact_duplicates": 0,
            "fuzzy_duplicates": 0,
        }

        for doc in docs:
            is_dup, dup_hash = self.is_duplicate(doc)

            if is_dup:
                duplicate_docs.append(doc)
                stats["duplicate_docs"] += 1

                # Determine if exact or fuzzy duplicate
                content_hash = self.get_content_hash(doc.page_content)
                if content_hash == dup_hash:
                    stats["exact_duplicates"] += 1
                else:
                    stats["fuzzy_duplicates"] += 1

                logger.debug(f"Duplicate document found: {dup_hash}")
            else:
                unique_docs.append(doc)
                self.add_document(doc)
                stats["unique_docs"] += 1

        logger.info(
            f"Deduplication completed: {stats['unique_docs']}/{stats['total_docs']} unique documents"
        )

        return unique_docs, duplicate_docs, stats

    def reset(self):
        """Reset deduplication tracking."""
        self.seen_hashes.clear()
        self.content_map.clear()


def create_default_validator() -> DocumentValidator:
    """Create a validator with default Vietnamese document settings."""
    forbidden_patterns = [
        r"^test\s*$",  # Test documents
        r"lorem\s+ipsum",  # Lorem ipsum placeholder text
        r"^\s*$",  # Empty/whitespace only
        r"password\s*:\s*\w+",  # Potential password leaks
    ]

    return DocumentValidator(
        min_length=30,
        max_length=100000,
        min_meaningful_ratio=0.6,
        forbidden_patterns=forbidden_patterns,
    )


def create_default_deduplicator() -> DocumentDeduplicator:
    """Create a deduplicator with default settings."""
    return DocumentDeduplicator(similarity_threshold=0.90)
