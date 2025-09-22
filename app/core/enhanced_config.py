"""
Configuration cải tiến cho hệ thống RAG
Thêm các tham số điều chỉnh cho enhanced features
"""

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


@dataclass
class Settings:
    # Database & Vector Store
    database_url: str = os.getenv("DATABASE_URL", "")
    collection: str = os.getenv("LC_COLLECTION", "docs")

    # Models
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-large")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Chunking
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))

    # File handling
    allowed_ext: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_EXT", ".pdf,.docx,.txt,.md").split(
            ","
        )
    )

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json: bool = os.getenv("LOG_JSON", "False").lower() in ("true", "1", "t")

    # RAG Enhancement Settings (MỚI)

    # Retrieval settings
    retrieval_k: int = int(os.getenv("RETRIEVAL_K", "5"))  # Số documents retrieve
    min_relevance_score: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.7"))

    # Query enhancement
    enable_query_enhancement: bool = (
        os.getenv("ENABLE_QUERY_ENHANCEMENT", "true").lower() == "true"
    )
    max_enhanced_queries: int = int(os.getenv("MAX_ENHANCED_QUERIES", "3"))

    # Document reranking
    enable_reranking: bool = os.getenv("ENABLE_RERANKING", "true").lower() == "true"
    rerank_top_k: int = int(
        os.getenv("RERANK_TOP_K", "10")
    )  # Retrieve nhiều rồi rerank xuống
    final_docs_k: int = int(os.getenv("FINAL_DOCS_K", "5"))  # Final docs sau rerank

    # Answer validation
    enable_answer_validation: bool = (
        os.getenv("ENABLE_ANSWER_VALIDATION", "false").lower() == "true"
    )
    min_citations_required: int = int(os.getenv("MIN_CITATIONS_REQUIRED", "1"))
    max_answer_length: int = int(os.getenv("MAX_ANSWER_LENGTH", "500"))  # words

    # Advanced features
    enable_conversation_memory: bool = (
        os.getenv("ENABLE_CONVERSATION_MEMORY", "false").lower() == "true"
    )
    memory_window: int = int(os.getenv("MEMORY_WINDOW", "5"))  # số turn gần nhất

    # Performance tuning
    parallel_processing: bool = (
        os.getenv("PARALLEL_PROCESSING", "true").lower() == "true"
    )
    cache_embeddings: bool = os.getenv("CACHE_EMBEDDINGS", "true").lower() == "true"

    # Quality control
    citation_check: bool = os.getenv("CITATION_CHECK", "true").lower() == "true"
    factual_consistency_check: bool = (
        os.getenv("FACTUAL_CONSISTENCY_CHECK", "false").lower() == "true"
    )

    # Fallback behaviors
    fallback_to_basic_rag: bool = (
        os.getenv("FALLBACK_TO_BASIC_RAG", "true").lower() == "true"
    )
    max_processing_time: int = int(os.getenv("MAX_PROCESSING_TIME", "30"))  # seconds


settings = Settings()


# Preset configurations cho different use cases
@dataclass
class RAGPresets:
    """Predefined configurations cho các use case khác nhau"""

    @staticmethod
    def get_fast_mode() -> dict:
        """Mode nhanh - ít enhancement"""
        return {
            "enable_query_enhancement": False,
            "enable_reranking": False,
            "enable_answer_validation": False,
            "retrieval_k": 3,
            "parallel_processing": True,
        }

    @staticmethod
    def get_quality_mode() -> dict:
        """Mode chất lượng cao - full enhancement"""
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,
            "enable_answer_validation": True,
            "rerank_top_k": 10,
            "final_docs_k": 5,
            "factual_consistency_check": True,
        }

    @staticmethod
    def get_balanced_mode() -> dict:
        """Mode cân bằng giữa tốc độ và chất lượng"""
        return {
            "enable_query_enhancement": True,
            "enable_reranking": True,
            "enable_answer_validation": False,
            "rerank_top_k": 8,
            "final_docs_k": 4,
            "parallel_processing": True,
        }


def apply_preset(preset_name: str) -> None:
    """Apply một preset configuration"""
    presets = {
        "fast": RAGPresets.get_fast_mode(),
        "quality": RAGPresets.get_quality_mode(),
        "balanced": RAGPresets.get_balanced_mode(),
    }

    if preset_name not in presets:
        raise ValueError(
            f"Unknown preset: {preset_name}. Available: {list(presets.keys())}"
        )

    preset_config = presets[preset_name]
    for key, value in preset_config.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
