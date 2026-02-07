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
    embed_model: str = os.getenv("EMBED_MODEL", "gemini-embedding-001")
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
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
    rag_mode: str = os.getenv("RAG_MODE", "fast")  # fast, balanced, quality

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

    # Chain of Thought (CoT) reasoning
    enable_cot_reasoning: bool = _env_bool("ENABLE_COT_REASONING", False)
    cot_analyzer_model: str = os.getenv("COT_ANALYZER_MODEL", "gemini-2.5-flash")

    # Fallback behaviors
    fallback_to_basic_rag: bool = _env_bool("FALLBACK_TO_BASIC_RAG", True)
    max_processing_time: int = int(os.getenv("MAX_PROCESSING_TIME", "30"))

    # User Upload Limits
    max_files_per_day: int = int(os.getenv("MAX_FILES_PER_DAY", "5"))
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    user_allowed_extensions: list[str] = field(
        default_factory=lambda: os.getenv(
            "USER_ALLOWED_EXTENSIONS", ".pdf,.docx,.txt,.doc"
        ).split(",")
    )

    # ===== Provider Settings (Phase 1 Abstraction) =====
    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")  # openai, vertex, gemini
    embed_provider: str = os.getenv("EMBED_PROVIDER", "vertex")  # openai, vertex
    reranker_provider: str = os.getenv(
        "RERANKER_PROVIDER", "vertex"
    )  # bge, openai, vertex

    # ===== Vertex AI / Google Cloud Settings =====
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-southeast1")
    vertex_llm_model: str = os.getenv("VERTEX_LLM_MODEL", "gemini-2.5-flash")
    vertex_embed_model: str = os.getenv("VERTEX_EMBED_MODEL", "gemini-embedding-001")
    embed_dimensions: int = int(
        os.getenv("EMBED_DIMENSIONS", "1536")
    )  # Vertex AI gemini-embedding-001 truncated to 1536

    # ===== Vertex AI Ranking API Settings =====
    vertex_reranker_model: str = os.getenv(
        "VERTEX_RERANKER_MODEL", "semantic-ranker-default@latest"
    )

    # ===== Gemini API Settings =====
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ===== Environment Mode (Phase 3) =====
    env_mode: str = os.getenv("ENV_MODE", "dev")  # dev, staging, production

    # ===== Cloud Database Settings (Phase 3) =====
    use_cloud_db: bool = _env_bool("USE_CLOUD_DB", False)
    cloud_db_host: str = os.getenv("CLOUD_DB_CONNECTION_PUBLICIP", "")
    cloud_db_user: str = os.getenv("CLOUD_DB_USER", "")
    cloud_db_password: str = os.getenv("CLOUD_DB_PASSWORD", "")
    cloud_db_name: str = os.getenv("CLOUD_INSTANCE_DB", "")
    cloud_db_connection_name: str = os.getenv("CLOUD_DB_CONNECTION_NAME", "")

    # ===== Cloud Storage Settings (Phase 3) =====
    use_gcs_storage: bool = _env_bool("USE_GCS_STORAGE", False)
    gcs_bucket: str = os.getenv("GCS_BUCKET", "")


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

    # NOTE: get_adaptive_mode() removed - use balanced mode instead


def apply_preset(preset_name: str) -> None:
    """Apply configuration preset to global settings."""
    presets = {
        "fast": RAGPresets.get_fast_mode(),
        "balanced": RAGPresets.get_balanced_mode(),
        "quality": RAGPresets.get_quality_mode(),
        # NOTE: adaptive removed - use balanced as default
    }

    if preset_name not in presets:
        raise ValueError(
            f"Unknown preset: {preset_name}. Available: fast, balanced, quality"
        )

    settings.rag_mode = preset_name
    for key, value in presets[preset_name].items():
        if hasattr(settings, key):
            setattr(settings, key, value)
