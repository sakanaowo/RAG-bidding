import os
import logging
from langchain_openai import OpenAIEmbeddings
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

logger = logging.getLogger(__name__)

embeddings = OpenAIEmbeddings(model=settings.embed_model)

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
    Wrapper class for PGVector store for upload service compatibility
    """

    def __init__(self):
        self.store = vector_store

    def add_texts(self, texts: list[str], metadatas: list[dict] = None):
        """Add texts with metadata to vector store"""
        return self.store.add_texts(texts, metadatas=metadatas)

    def add_documents(self, documents):
        """Add documents to vector store"""
        return self.store.add_documents(documents)

    def similarity_search(self, query: str, k: int = 5):
        """Search for similar documents"""
        return self.store.similarity_search(query, k=k)
