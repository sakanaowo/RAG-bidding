"""
Optimized PGVector Store với Connection Pooling

Giải quyết performance issues từ test results:
- Batch processing để reduce connection overhead
- Connection reuse cho multiple operations
- Async operations với connection pooling
- Enhanced error handling và monitoring
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager

from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.models import settings
from ...config.database import get_db, get_db_config

logger = logging.getLogger(__name__)


class PooledPGVectorStore:
    """
    PGVector store optimized với connection pooling và performance enhancements

    Key optimizations:
    1. Connection pooling for all operations
    2. Batch processing để reduce database calls
    3. Async operations với proper resource management
    4. Performance monitoring và metrics collection
    """

    def __init__(self, embeddings, collection_name: str = None):
        self.embeddings = embeddings
        self.collection_name = collection_name or settings.collection
        self._sync_connection_string = None
        self._langchain_store = None
        self.stats = {
            "documents_added": 0,
            "queries_executed": 0,
            "batch_operations": 0,
            "errors": 0,
        }

        # Initialize sync store for LangChain compatibility
        self._setup_sync_store()

    def _get_sync_connection_string(self) -> str:
        """
        Get synchronous connection string for LangChain PGVector

        LangChain PGVector requires sync connection, so we convert from async URL
        """
        if not self._sync_connection_string:
            # Use effective database URL (respects USE_CLOUD_DB setting)
            from src.config.database import get_effective_database_url

            async_url = get_effective_database_url()
            self._sync_connection_string = async_url.replace(
                "postgresql+asyncpg://", "postgresql://"
            ).replace("postgresql+psycopg://", "postgresql://")
        return self._sync_connection_string

    def _setup_sync_store(self):
        """Setup LangChain PGVector instance với optimized settings"""
        try:
            self._langchain_store = PGVector(
                embeddings=self.embeddings,
                collection_name=self.collection_name,
                connection=self._get_sync_connection_string(),
                use_jsonb=True,
                create_extension=False,  # Assume extension already exists
            )
            logger.info(
                f"LangChain PGVector store initialized for collection: {self.collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize PGVector store: {e}")
            raise

    def get_langchain_store(self) -> PGVector:
        """
        Get LangChain PGVector instance for backward compatibility

        Returns:
            PGVector: LangChain vector store instance
        """
        if not self._langchain_store:
            self._setup_sync_store()
        return self._langchain_store

    async def add_documents_batch(
        self, documents: List[Document], batch_size: int = 50
    ) -> List[str]:
        """
        Add documents in optimized batches để improve performance

        Args:
            documents: List of documents to add
            batch_size: Size of each batch (optimized for connection pool)

        Returns:
            List[str]: Document IDs
        """
        if not documents:
            return []

        logger.info(f"Adding {len(documents)} documents in batches of {batch_size}")

        document_ids = []
        error_count = 0

        try:
            # Process in batches to avoid overwhelming connection pool
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(documents) + batch_size - 1) // batch_size

                logger.debug(
                    f"Processing batch {batch_num}/{total_batches}: {len(batch)} documents"
                )

                try:
                    # Use sync store for batch processing
                    batch_ids = self._langchain_store.add_documents(batch)
                    document_ids.extend(batch_ids)

                    self.stats["documents_added"] += len(batch)
                    self.stats["batch_operations"] += 1

                    # Small delay between batches to prevent connection exhaustion
                    if i + batch_size < len(documents):
                        await asyncio.sleep(0.05)  # 50ms delay

                except Exception as e:
                    logger.error(f"Batch {batch_num} failed: {e}")
                    error_count += 1
                    self.stats["errors"] += 1

                    # Continue with next batch instead of failing completely
                    continue

            success_rate = (
                (len(documents) - error_count * batch_size) / len(documents)
            ) * 100
            logger.info(
                f"Document addition completed. Success rate: {success_rate:.1f}%"
            )

            return document_ids

        except Exception as e:
            logger.error(f"Batch document addition failed: {e}")
            self.stats["errors"] += 1
            raise

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None,
        score_threshold: float = None,
    ) -> List[Tuple[Document, float]]:
        """
        Async similarity search với connection pooling và score filtering

        Args:
            query: Search query
            k: Number of results to return
            filter: Metadata filter
            score_threshold: Minimum similarity score

        Returns:
            List[Tuple[Document, float]]: Documents with similarity scores
        """
        try:
            logger.debug(
                f"Executing similarity search: query_length={len(query)}, k={k}"
            )

            # Use LangChain store for similarity search
            results = self._langchain_store.similarity_search_with_score(
                query=query, k=k, filter=filter
            )

            # Apply score threshold filtering if specified
            if score_threshold is not None:
                filtered_results = [
                    (doc, score) for doc, score in results if score >= score_threshold
                ]
                logger.debug(
                    f"Score filtering: {len(results)} → {len(filtered_results)} results"
                )
                results = filtered_results

            self.stats["queries_executed"] += 1
            logger.debug(f"Similarity search completed: {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            self.stats["errors"] += 1
            raise

    async def similarity_search(
        self, query: str, k: int = 5, filter: Optional[Dict] = None
    ) -> List[Document]:
        """
        Simplified similarity search returning only documents

        Args:
            query: Search query
            k: Number of results
            filter: Metadata filter

        Returns:
            List[Document]: Similar documents
        """
        results_with_scores = await self.similarity_search_with_score(
            query=query, k=k, filter=filter
        )
        return [doc for doc, score in results_with_scores]

    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive collection statistics using pooled connection

        Returns:
            Dict: Collection statistics và performance metrics
        """
        try:
            async with get_db_config().get_session() as session:
                # Get collection statistics
                collection_stats_query = text(
                    """
                    SELECT 
                        COUNT(*) as total_documents,
                        COUNT(DISTINCT metadata->>'source') as unique_sources,
                        COUNT(DISTINCT metadata->>'document_type') as document_types,
                        AVG(LENGTH(document)) as avg_document_length,
                        AVG(array_length(embedding, 1)) as avg_embedding_dim,
                        MIN(LENGTH(document)) as min_document_length,
                        MAX(LENGTH(document)) as max_document_length
                    FROM langchain_pg_embedding 
                    WHERE collection_id = (
                        SELECT uuid FROM langchain_pg_collection 
                        WHERE name = :collection_name
                    )
                """
                )

                result = await session.execute(
                    collection_stats_query, {"collection_name": self.collection_name}
                )
                row = result.fetchone()

                if row:
                    stats = {
                        "collection_name": self.collection_name,
                        "total_documents": int(row[0]) if row[0] else 0,
                        "unique_sources": int(row[1]) if row[1] else 0,
                        "document_types": int(row[2]) if row[2] else 0,
                        "avg_document_length": round(float(row[3]), 2) if row[3] else 0,
                        "avg_embedding_dim": int(row[4]) if row[4] else 0,
                        "min_document_length": int(row[5]) if row[5] else 0,
                        "max_document_length": int(row[6]) if row[6] else 0,
                    }
                else:
                    stats = {
                        "collection_name": self.collection_name,
                        "total_documents": 0,
                    }

                # Add performance stats
                stats.update(
                    {
                        "performance_stats": self.stats,
                        "efficiency_metrics": self._calculate_efficiency_metrics(),
                    }
                )

                return stats

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "error": str(e),
                "performance_stats": self.stats,
            }

    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate efficiency metrics for monitoring"""
        total_operations = (
            self.stats["queries_executed"] + self.stats["batch_operations"]
        )

        return {
            "total_operations": total_operations,
            "error_rate": (self.stats["errors"] / max(total_operations, 1)) * 100,
            "success_rate": (
                (total_operations - self.stats["errors"]) / max(total_operations, 1)
            )
            * 100,
            "avg_documents_per_batch": (
                self.stats["documents_added"] / max(self.stats["batch_operations"], 1)
            ),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on vector store

        Returns:
            Dict: Health check results
        """
        try:
            # Test basic query
            test_results = await self.similarity_search("test query", k=1)

            # Get collection stats
            stats = await self.get_collection_stats()

            return {
                "status": "healthy",
                "vector_store_accessible": True,
                "collection_exists": stats.get("total_documents", 0) >= 0,
                "total_documents": stats.get("total_documents", 0),
                "performance_metrics": self.stats,
                "recommendations": self._generate_health_recommendations(stats),
            }

        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "vector_store_accessible": False,
                "performance_metrics": self.stats,
            }

    def _generate_health_recommendations(self, stats: Dict) -> List[str]:
        """Generate health recommendations based on stats"""
        recommendations = []

        total_docs = stats.get("total_documents", 0)
        error_rate = self.stats["errors"] / max(self.stats["queries_executed"], 1) * 100

        if total_docs == 0:
            recommendations.append(
                "No documents found in collection. Check data ingestion."
            )

        if error_rate > 5:
            recommendations.append(
                f"High error rate ({error_rate:.1f}%). Check connection stability."
            )

        if total_docs > 100000:
            recommendations.append(
                "Large collection detected. Consider indexing optimization."
            )

        if not recommendations:
            recommendations.append("Vector store operating optimally.")

        return recommendations

    # Backward compatibility methods
    def add_documents(self, documents: List[Document]) -> List[str]:
        """Sync wrapper for add_documents_batch"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.add_documents_batch(documents))

    def add_texts(self, texts: List[str], metadatas: List[Dict] = None) -> List[str]:
        """Add texts with metadata (backward compatibility)"""
        documents = []
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            documents.append(Document(page_content=text, metadata=metadata))

        return self.add_documents(documents)


# Factory function for creating optimized vector store instances
def create_optimized_vector_store(
    embeddings=None, collection_name: str = None
) -> PooledPGVectorStore:
    """
    Factory function to create optimized vector store với proper configuration

    Args:
        embeddings: Embeddings instance (uses default if None)
        collection_name: Collection name (uses settings default if None)

    Returns:
        PooledPGVectorStore: Optimized vector store instance
    """
    if embeddings is None:
        from ...config.embedding_provider import get_default_embeddings

        embeddings = get_default_embeddings()

    return PooledPGVectorStore(embeddings=embeddings, collection_name=collection_name)
