"""
SQLAlchemy Models Package
Centralized database models for RAG Bidding System
"""

from .base import Base, engine, SessionLocal, get_db
from .documents import Document
from .embeddings import LangchainPGEmbedding, LangchainPGCollection

# Future models (v2.1+)
# from .users import User
# from .chat_sessions import ChatSession, ChatMessage
# from .query_logs import QueryLog
# from .upload_jobs import DocumentUploadJob

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "Document",
    "LangchainPGEmbedding",
    "LangchainPGCollection",
]
