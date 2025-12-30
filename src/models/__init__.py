"""
SQLAlchemy Models Package - Schema v3
Centralized database models for RAG Bidding System
"""

from .base import Base, engine, SessionLocal, get_db

# Core models
from .documents import Document
from .embeddings import LangchainPGEmbedding, LangchainPGCollection
from .document_chunks import DocumentChunk

# User & Auth models
from .users import User

# Chat models
from .conversations import Conversation
from .messages import Message
from .citations import Citation

# Analytics models
from .feedback import Feedback
from .queries import Query
from .user_metrics import UserUsageMetric

__all__ = [
    # Base
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    # Core
    "Document",
    "DocumentChunk",
    "LangchainPGEmbedding",
    "LangchainPGCollection",
    # User & Auth
    "User",
    # Chat
    "Conversation",
    "Message",
    "Citation",
    # Analytics
    "Feedback",
    "Query",
    "UserUsageMetric",
]
