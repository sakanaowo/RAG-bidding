"""
Vertex AI Reranker using Discovery Engine Ranking API

Uses Google Cloud Discovery Engine's Ranking API to rerank documents
based on semantic relevance to a query.

Requirements:
    pip install google-cloud-discoveryengine>=0.12.0
    
Configuration:
    GOOGLE_CLOUD_PROJECT: GCP project ID
    VERTEX_RERANKER_MODEL: Model name (default: semantic-ranker-default@latest)
"""

import logging
from typing import List, Tuple, Optional

from langchain_core.documents import Document

from .base_reranker import BaseReranker

logger = logging.getLogger(__name__)


class VertexAIReranker(BaseReranker):
    """
    Reranker using Vertex AI / Discovery Engine Ranking API.
    
    Provides fast, accurate semantic reranking with <100ms latency.
    Supports up to 1024 tokens per record (model v004+).
    """
    
    def __init__(
        self,
        project: Optional[str] = None,
        location: str = "global",
        model: Optional[str] = None,
        ranking_config: str = "default_ranking_config",
    ):
        """
        Initialize Vertex AI Reranker.
        
        Args:
            project: GCP project ID. Defaults to GOOGLE_CLOUD_PROJECT env var.
            location: API location. Default "global".
            model: Ranking model. Default from settings.vertex_reranker_model.
            ranking_config: Ranking config name. Default "default_ranking_config".
        """
        from src.config.models import settings
        
        self.project = project or settings.google_cloud_project
        self.location = location
        self.model = model or settings.vertex_reranker_model
        self.ranking_config_name = ranking_config
        
        if not self.project:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is required for Vertex AI Reranker. "
                "Set via environment variable or pass project parameter."
            )
        
        # Initialize client lazily
        self._client = None
        self._ranking_config = None
        
        logger.info(
            f"✅ Initialized Vertex AI Reranker: project={self.project}, "
            f"model={self.model}"
        )
    
    def _get_client(self):
        """Lazy initialization of Discovery Engine client."""
        if self._client is None:
            try:
                from google.cloud import discoveryengine_v1 as discoveryengine
            except ImportError:
                raise ImportError(
                    "google-cloud-discoveryengine package not installed. "
                    "Run: pip install google-cloud-discoveryengine>=0.12.0"
                )
            
            self._client = discoveryengine.RankServiceClient()
            self._ranking_config = self._client.ranking_config_path(
                project=self.project,
                location=self.location,
                ranking_config=self.ranking_config_name,
            )
        
        return self._client
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5,
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents based on query relevance using Vertex AI Ranking API.
        
        Args:
            query: The search query
            documents: List of LangChain Document objects to rerank
            top_k: Number of top documents to return
            
        Returns:
            List of (document, score) tuples, sorted by relevance
        """
        if not documents:
            return []
        
        try:
            from google.cloud import discoveryengine_v1 as discoveryengine
        except ImportError:
            raise ImportError(
                "google-cloud-discoveryengine package not installed. "
                "Run: pip install google-cloud-discoveryengine>=0.12.0"
            )
        
        client = self._get_client()
        
        # Convert LangChain documents to RankingRecords
        records = []
        doc_map = {}  # Map record ID to original document
        
        for i, doc in enumerate(documents):
            record_id = str(i)
            doc_map[record_id] = doc
            
            # Extract title from metadata if available
            title = doc.metadata.get("title", doc.metadata.get("source", ""))
            content = doc.page_content
            
            # Truncate content if too long (1024 token limit for v004+)
            # Rough estimate: 1 token ≈ 4 chars
            max_chars = 4000
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
            
            records.append(
                discoveryengine.RankingRecord(
                    id=record_id,
                    title=title[:200] if title else "",  # Title limit
                    content=content,
                )
            )
        
        # Call Ranking API
        request = discoveryengine.RankRequest(
            ranking_config=self._ranking_config,
            model=self.model,
            top_n=min(top_k, len(documents)),
            query=query,
            records=records,
        )
        
        try:
            response = client.rank(request=request)
        except Exception as e:
            logger.error(f"Vertex AI Ranking API error: {e}")
            # Fallback: return original order with 0 scores
            return [(doc, 0.0) for doc in documents[:top_k]]
        
        # Parse response and map back to documents
        results = []
        for record in response.records:
            if record.id in doc_map:
                doc = doc_map[record.id]
                score = record.score
                results.append((doc, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(
            f"Vertex AI Reranker: query='{query[:50]}...', "
            f"input={len(documents)}, output={len(results)}"
        )
        
        return results


# Singleton instance
_vertex_reranker: Optional[VertexAIReranker] = None


def get_vertex_reranker(**kwargs) -> VertexAIReranker:
    """Get or create singleton Vertex AI Reranker instance."""
    global _vertex_reranker
    
    if _vertex_reranker is None:
        _vertex_reranker = VertexAIReranker(**kwargs)
    
    return _vertex_reranker


def reset_vertex_reranker() -> None:
    """Reset singleton Vertex AI Reranker instance."""
    global _vertex_reranker
    _vertex_reranker = None
    logger.info("🔄 Reset Vertex AI Reranker singleton")
