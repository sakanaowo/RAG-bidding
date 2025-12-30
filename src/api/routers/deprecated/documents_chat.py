"""
Chat API Router - Session-based conversational interface

Endpoints:
1. POST /chat/sessions - Create new chat session
2. POST /chat/sessions/{session_id}/messages - Send message
3. GET /chat/sessions/{session_id}/history - Get conversation history
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.api.chat_session import RedisChatSessionStore, ContextWindowManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


# ===== MODELS =====


class ChatSessionResponse(BaseModel):
    """Chat session creation response."""

    session_id: str
    created_at: str


class ChatMessage(BaseModel):
    """Chat message input."""

    message: str = Field(..., min_length=1, max_length=5000)
    metadata: Optional[Dict[str, Any]] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response."""

    session_id: str
    messages: List[Dict[str, Any]]
    total_messages: int


# ---------------------------------------------------------------------------
# 🔹 CHAT SESSION ENDPOINTS
# ---------------------------------------------------------------------------


# TODO [CHAT-MIGRATION]: Replace Redis with PostgreSQL for chat sessions
# See: /documents/technical/implementation-plans/CHAT_SESSION_POSTGRESQL_PLAN.md
# Current: RedisChatSessionStore (temporary)
# Target: PostgresChatSessionStore (persistent, queryable)
# Changes needed:
#   1. Disable ENABLE_REDIS_SESSIONS in .env
#   2. Replace RedisChatSessionStore → PostgresChatSessionStore
#   3. Add session_title auto-generation
#   4. Update endpoint responses with session metadata
# Estimated: 1.5 hours

# Session storage configuration
# ✅ Redis is installed and running - Enable Redis sessions
from src.config.feature_flags import ENABLE_REDIS_SESSIONS

# Initialize session store (singleton)
_session_store = None


def get_session_store():
    """
    Get or create session store singleton.

    Current: In-memory storage (development mode)
    TODO [CHAT-MIGRATION]: Enable PostgreSQL for production
    Replace RedisChatSessionStore with PostgresChatSessionStore

    See implementation plan: documents/technical/implementation-plans/CHAT_SESSION_POSTGRESQL_PLAN.md
    """
    global _session_store

    if _session_store is None:
        if ENABLE_REDIS_SESSIONS:
            try:
                # Redis storage (production-ready)
                # TODO [CHAT-MIGRATION]: Replace this entire block with PostgresChatSessionStore
                _session_store = RedisChatSessionStore(
                    redis_host="localhost",
                    redis_port=6379,
                    redis_db=1,
                    session_ttl=3600,
                )
                # Test connection
                _session_store.redis_client.ping()
                logger.info("✅ Chat session using Redis storage")
            except Exception as e:
                logger.warning(
                    f"⚠️ Redis connection failed ({e}), falling back to in-memory storage"
                )
                _session_store = InMemorySessionStore()
        else:
            # In-memory storage (development only)
            logger.info("💾 Chat sessions: IN-MEMORY mode (non-persistent)")
            logger.info(
                "   → To enable Redis: Set ENABLE_REDIS_SESSIONS=True + install Redis"
            )
            _session_store = InMemorySessionStore()

    return _session_store


class InMemorySessionStore:
    """
    Simple in-memory session store as fallback when Redis is unavailable.

    ⚠️ WARNING: Sessions are lost on server restart!
    For production, use Redis or PostgreSQL.
    """

    def __init__(self):
        self._sessions = {}  # session_id -> session data
        logger.info("💾 Initialized in-memory session store (non-persistent)")

    def create_session(self, user_id: Optional[str] = None) -> str:
        """Create new session."""
        import uuid

        session_id = str(uuid.uuid4())

        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
        }

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        return self._sessions.get(session_id)

    def add_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ):
        """Add message to session."""
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} not found")

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        self._sessions[session_id]["messages"].append(message)

    def get_history(self, session_id: str, max_messages: int = 50) -> List[Dict]:
        """Get conversation history."""
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session["messages"]
        return messages[-max_messages:] if len(messages) > max_messages else messages

    def clear_session(self, session_id: str):
        """Delete session."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def get_active_sessions(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get all active sessions."""
        sessions = list(self._sessions.values())

        if user_id:
            sessions = [s for s in sessions if s.get("user_id") == user_id]

        return [
            {"session_id": s["session_id"], "created_at": s["created_at"]}
            for s in sessions
        ]


@router.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    user_id: Optional[str] = None,
):
    """
    Create new chat session.

    Args:
        user_id: Optional user identifier for tracking

    Returns:
        session_id: UUID for this conversation

    Example:
        POST /chat/sessions
        Response: {"session_id": "abc-123-...", "created_at": "2025-11-13T..."}
    """
    try:
        store = get_session_store()
        session_id = store.create_session(user_id=user_id)

        logger.info(f"💬 Created chat session: {session_id} (user: {user_id})")

        return {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: str,
    message: ChatMessage,
):
    """
    Send message to chat session and get AI response.

    Args:
        session_id: Session UUID
        message: User message

    Returns:
        AI response with sources

    Example:
        POST /chat/sessions/abc-123/messages
        Body: {"message": "điều kiện tham gia đấu thầu?"}
    """
    try:
        store = get_session_store()

        # Verify session exists
        session = store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        # Add user message to history
        store.add_message(
            session_id=session_id,
            role="user",
            content=message.message,
            metadata=message.metadata,
        )

        # Get conversation history for context
        history = store.get_history(session_id, max_messages=10)

        # Call RAG pipeline (reuse existing answer() function)
        from src.generation.chains.qa_chain import answer

        result = answer(
            question=message.message,
            mode="balanced",
            reranker_type="bge",  # Default BGE reranker
        )

        # Add AI response to history
        store.add_message(
            session_id=session_id,
            role="assistant",
            content=result["answer"],
            metadata={
                "sources": result.get("sources", []),
                "processing_time_ms": result.get("processing_time_ms"),
            },
        )

        logger.info(f"💬 Session {session_id}: User message processed")

        return {
            "session_id": session_id,
            "user_message": message.message,
            "assistant_response": result["answer"],
            "sources": result.get("sources", []),
            "processing_time_ms": result.get("processing_time_ms"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    max_messages: int = Query(default=50, le=200),
):
    """
    Get conversation history for a session.

    Args:
        session_id: Session UUID
        max_messages: Max messages to return (recent first)

    Returns:
        List of messages with metadata
    """
    try:
        store = get_session_store()

        # Verify session exists
        session = store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        # Get history
        messages = store.get_history(session_id, max_messages=max_messages)

        logger.info(f"💬 Retrieved {len(messages)} messages for session {session_id}")

        return {
            "session_id": session_id,
            "messages": messages,
            "total_messages": len(session.get("messages", [])),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
):
    """
    Delete chat session and all messages.

    Args:
        session_id: Session UUID to delete
    """
    try:
        store = get_session_store()
        store.clear_session(session_id)

        logger.info(f"💬 Deleted session: {session_id}")

        return {"message": f"Session {session_id} deleted"}

    except Exception as e:
        logger.error(f"❌ Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/sessions")
async def list_chat_sessions(
    user_id: Optional[str] = None,
):
    """
    List all active chat sessions.

    Args:
        user_id: Optional filter by user ID

    Returns:
        List of active session IDs
    """
    try:
        store = get_session_store()
        sessions = store.get_active_sessions(user_id=user_id)

        logger.info(f"💬 Found {len(sessions)} active sessions")

        return {
            "sessions": sessions,
            "total": len(sessions),
        }

    except Exception as e:
        logger.error(f"❌ Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
