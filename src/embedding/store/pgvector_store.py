import os
import logging
from langchain_postgres import PGVector
from src.config.models import settings
from src.config.feature_flags import (
    ENABLE_REDIS_CACHE,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB_CACHE,
    CACHE_TTL_RETRIEVAL,
    ENABLE_L1_CACHE,
    L1_CACHE_MAXSIZE,
)
from src.config.embedding_provider import get_default_embeddings

logger = logging.getLogger(__name__)

# Use embedding factory (supports OpenAI, Vertex AI based on EMBED_PROVIDER)
embeddings = get_default_embeddings()

# Create base vector store
_raw_vector_store = PGVector(
    embeddings=embeddings,
    collection_name=settings.collection,
    connection=settings.database_url,
    use_jsonb=True,
    create_extension=True,
)

# Wrap with cache if enabled
if ENABLE_REDIS_CACHE:
    try:
        from src.retrieval.cached_retrieval import CachedVectorStore

        vector_store = CachedVectorStore(
            vector_store=_raw_vector_store,
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            redis_db=REDIS_DB_CACHE,
            ttl=CACHE_TTL_RETRIEVAL,
            enable_l1_cache=ENABLE_L1_CACHE,
            l1_cache_size=L1_CACHE_MAXSIZE,
        )
        logger.info(
            f"✅ Vector store cache ENABLED: "
            f"L1={'ON' if ENABLE_L1_CACHE else 'OFF'} (maxsize={L1_CACHE_MAXSIZE}), "
            f"L2=ON (Redis DB {REDIS_DB_CACHE}), "
            f"TTL={CACHE_TTL_RETRIEVAL}s"
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Failed to enable cache: {e}. " f"Falling back to direct PostgreSQL."
        )
        vector_store = _raw_vector_store
else:
    vector_store = _raw_vector_store
    logger.info("ℹ️ Cache DISABLED - using direct PostgreSQL vector store")


def bootstrap():
    """Bootstrap database using raw vector store (not cached wrapper)"""
    _raw_vector_store.create_vector_extension()
    _raw_vector_store.create_tables_if_not_exists()
    _raw_vector_store.create_collection()


class PGVectorStore:
    """
    Wrapper class for PGVector store.

    Write operations (add_texts, add_documents) always use raw vector store.
    Read operations (similarity_search) use cached wrapper if enabled.
    """

    def __init__(self):
        # Use cached wrapper for reads (if available)
        self.store = vector_store
        # Always use raw vector store for writes (bypass cache)
        self._raw_store = _raw_vector_store

    def add_texts(self, texts: list[str], metadatas: list[dict] = None):
        """Add texts with metadata to vector store (bypasses cache)"""
        return self._raw_store.add_texts(texts, metadatas=metadatas)

    def add_documents(self, documents):
        """Add documents to vector store (bypasses cache)"""
        return self._raw_store.add_documents(documents)

    def similarity_search(self, query: str, k: int = 5, **kwargs):
        """Search for similar documents (uses cache if enabled)

        Args:
            query: Search query
            k: Number of results
            **kwargs: Additional parameters (e.g. filter for metadata filtering)
        """
        return self.store.similarity_search(query, k=k, **kwargs)

    def clear_cache(self):
        """
        Clear all retrieval caches (L1 + L2).

        Call this after admin operations that change document visibility:
        - Update document status (active/expired)
        - Delete documents
        - Bulk updates to metadata

        Returns:
            dict: Statistics about cleared cache (if cache enabled)
            None: If cache is disabled
        """
        # Only clear if using cached wrapper
        if hasattr(self.store, "clear_all_caches"):
            return self.store.clear_all_caches()
        else:
            # Cache disabled, nothing to clear
            import logging

            logger = logging.getLogger(__name__)
            logger.info("ℹ️  Cache disabled - no cache to clear")
            return None
