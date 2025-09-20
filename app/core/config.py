import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    collection: str = os.getenv("LC_COLLECTION", "docs")
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-large")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    allowed_ext: list[str] = os.getenv("ALLOWED_EXT", ".pdf,.docx,.txt,.md").split(",")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_json: bool = os.getenv("LOG_JSON", "False").lower() in ("true", "1", "t")


settings = Settings()
