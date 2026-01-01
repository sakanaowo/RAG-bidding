import os
from dataclasses import dataclass, field
from typing import Dict

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean value from environment variables."""
    return os.getenv(name, "true" if default else "false").lower() in (
        "true",
        "1",
        "t",
        "yes",
    )


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    collection: str = os.getenv("LC_COLLECTION", "docs")
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    allowed_ext: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_EXT", ".pdf,.docx,.txt,.md").split(
            ","
        )
    )
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json: bool = _env_bool("LOG_JSON", False)

    # Phase 1 Enhanced Features - Quick Wins
    enable_adaptive_retrieval: bool = _env_bool("ENABLE_ADAPTIVE_RETRIEVAL", True)
    enable_enhanced_prompts: bool = _env_bool("ENABLE_ENHANCED_PROMPTS", True)
    rag_mode: str = os.getenv("RAG_MODE", "balanced")  # fast, balanced, quality

    # Retrieval tuning
    retrieval_k: int = int(os.getenv("RETRIEVAL_K", "5"))
    min_relevance_score: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.7"))

    # Query enhancement
    enable_query_enhancement: bool = _env_bool("ENABLE_QUERY_ENHANCEMENT", True)
    max_enhanced_queries: int = int(os.getenv("MAX_ENHANCED_QUERIES", "3"))

    # Document reranking
    enable_reranking: bool = _env_bool("ENABLE_RERANKING", True)
    reranker_model: str = os.getenv(
        "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
    )  # BGE multilingual reranker
    reranker_device: str = os.getenv("RERANKER_DEVICE", "auto")  # auto, cuda, cpu
    reranker_batch_size: int = int(os.getenv("RERANKER_BATCH_SIZE", "32"))
    rerank_top_k: int = int(os.getenv("RERANK_TOP_K", "10"))
    final_docs_k: int = int(os.getenv("FINAL_DOCS_K", "5"))

    # Answer validation
    enable_answer_validation: bool = _env_bool("ENABLE_ANSWER_VALIDATION", False)
    min_citations_required: int = int(os.getenv("MIN_CITATIONS_REQUIRED", "1"))
    max_answer_length: int = int(os.getenv("MAX_ANSWER_LENGTH", "500"))

    # Conversation memory
    enable_conversation_memory: bool = _env_bool("ENABLE_CONVERSATION_MEMORY", False)
    memory_window: int = int(os.getenv("MEMORY_WINDOW", "5"))

    # Performance tuning
    parallel_processing: bool = _env_bool("PARALLEL_PROCESSING", True)
    cache_embeddings: bool = _env_bool("CACHE_EMBEDDINGS", True)

    # Quality control
    citation_check: bool = _env_bool("CITATION_CHECK", True)
    factual_consistency_check: bool = _env_bool("FACTUAL_CONSISTENCY_CHECK", False)

    # Fallback behaviors
    fallback_to_basic_rag: bool = _env_bool("FALLBACK_TO_BASIC_RAG", True)
    max_processing_time: int = int(os.getenv("MAX_PROCESSING_TIME", "30"))


settings = Settings()


class RAGPresets:
    """Predefined configurations for different operating modes."""

    @staticmethod
    def get_fast_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": False,
            "enable_reranking": False,
            "enable_answer_validation": False,
            "retrieval_k": 3,
            "parallel_processing": True,
        }

    @staticmethod
    def get_quality_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,
            "enable_answer_validation": True,
            "rerank_top_k": 10,
            "final_docs_k": 5,
            "factual_consistency_check": True,
        }

    @staticmethod
    def get_balanced_mode() -> Dict[str, object]:
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,
            "enable_answer_validation": False,
            "rerank_top_k": 8,
            "final_docs_k": 4,
            "parallel_processing": True,
        }

    @staticmethod
    def get_adaptive_mode() -> Dict[str, object]:
        """Adaptive mode: Query enhancement + dynamic K selection."""
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,
            "enable_answer_validation": False,
            "retrieval_k": 5,  # Will be adjusted by AdaptiveKRetriever
            "parallel_processing": True,
        }


def apply_preset(preset_name: str) -> None:
    """Apply configuration preset to global settings."""
    presets = {
        "fast": RAGPresets.get_fast_mode(),
        "balanced": RAGPresets.get_balanced_mode(),
        "quality": RAGPresets.get_quality_mode(),
        "adaptive": RAGPresets.get_adaptive_mode(),
    }

    if preset_name not in presets:
        raise ValueError(
            f"Unknown preset: {preset_name}. Available presets: {list(presets.keys())}"
        )

    settings.rag_mode = preset_name
    for key, value in presets[preset_name].items():
        if hasattr(settings, key):
            setattr(settings, key, value)
