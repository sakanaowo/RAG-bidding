"""
Add metadata-based filtering to retriever.

This approach:
- Does NOT update existing data
- Filters at query time based on metadata
- Can be combined with Cách 1 or 2 after updating metadata

Usage in retriever:
    retriever = BaseVectorRetriever(
        k=5,
        filter={"status": "active"}  # Only retrieve active documents
    )
"""

from langchain_core.documents import Document
from typing import List, Optional, Dict
from datetime import datetime


class MetadataFilter:
    """Filter documents based on metadata criteria."""

    @staticmethod
    def is_active(doc: Document) -> bool:
        """Check if document is active."""
        status = doc.metadata.get("status")
        if status:
            return status == "active"

        # Fallback: check valid_until date
        valid_until = doc.metadata.get("valid_until")
        if valid_until:
            try:
                valid_date = datetime.strptime(valid_until, "%Y-%m-%d")
                return valid_date >= datetime.now()
            except:
                pass

        # Default: assume active if no metadata
        return True

    @staticmethod
    def filter_by_status(
        docs: List[Document], status: str = "active"
    ) -> List[Document]:
        """Filter documents by status."""
        if status == "active":
            return [doc for doc in docs if MetadataFilter.is_active(doc)]
        elif status == "expired":
            return [doc for doc in docs if not MetadataFilter.is_active(doc)]
        else:
            return docs  # No filter

    @staticmethod
    def filter_by_date_range(
        docs: List[Document],
        min_date: Optional[str] = None,
        max_date: Optional[str] = None,
    ) -> List[Document]:
        """Filter documents by valid_until date range."""
        filtered = []

        for doc in docs:
            valid_until = doc.metadata.get("valid_until")
            if not valid_until:
                continue

            try:
                doc_date = datetime.strptime(valid_until, "%Y-%m-%d")

                if min_date:
                    min_dt = datetime.strptime(min_date, "%Y-%m-%d")
                    if doc_date < min_dt:
                        continue

                if max_date:
                    max_dt = datetime.strptime(max_date, "%Y-%m-%d")
                    if doc_date > max_dt:
                        continue

                filtered.append(doc)
            except:
                continue

        return filtered


# Example usage in base_vector_retriever.py:
"""
from src.retrieval.filters.metadata_filter import MetadataFilter

class BaseVectorRetriever:
    def __init__(self, k=5, filter_status="active"):
        self.k = k
        self.filter_status = filter_status
    
    def _get_relevant_documents(self, query):
        # Retrieve more documents (k*2) if filtering
        retrieve_k = self.k * 2 if self.filter_status else self.k
        
        docs = vector_store.similarity_search(query, k=retrieve_k)
        
        # Apply metadata filter
        if self.filter_status:
            docs = MetadataFilter.filter_by_status(docs, self.filter_status)
        
        # Return top k after filtering
        return docs[:self.k]
"""
