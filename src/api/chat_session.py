"""
Chat Session Management - Production Implementation

Covers:
1. Session storage strategies
2. Conversation history management
3. Context window optimization
4. Multi-user session isolation
"""

import uuid
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import redis
import json

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.memory import ConversationBufferMemory, ConversationSummaryMemory


# ===== OPTION 1: Redis-based Session Store (Recommended) =====


class RedisChatSessionStore:
    """
    Redis-based chat session storage.

    Pros:
    - Fast (sub-millisecond)
    - Scalable across multiple API servers
    - TTL-based expiration (auto cleanup)
    - Shared state for load-balanced servers

    Cons:
    - Requires Redis server
    - Lost on Redis restart (unless persisted)

    Best for: Production with multiple API instances
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 1,  # Use different DB from cache
        session_ttl: int = 3600,  # 1 hour default
    ):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True,  # JSON strings
        )
        self.session_ttl = session_ttl

    def create_session(self, user_id: str = None) -> str:
        """
        Create new chat session.

        Args:
            user_id: Optional user identifier

        Returns:
            session_id: UUID for this conversation
        """
        session_id = str(uuid.uuid4())

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "messages": [],
            "metadata": {},
        }

        # Store in Redis with TTL
        key = f"chat:session:{session_id}"
        self.redis.setex(key, self.session_ttl, json.dumps(session_data))

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        key = f"chat:session:{session_id}"
        data = self.redis.get(key)

        if data:
            # Extend TTL on access (keep active sessions alive)
            self.redis.expire(key, self.session_ttl)
            return json.loads(data)

        return None

    def add_message(
        self,
        session_id: str,
        role: str,  # "user" or "assistant"
        content: str,
        metadata: Dict = None,
    ):
        """Add message to session history."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }

        session["messages"].append(message)
        session["last_activity"] = datetime.utcnow().isoformat()

        # Update Redis
        key = f"chat:session:{session_id}"
        self.redis.setex(key, self.session_ttl, json.dumps(session))

    def get_history(self, session_id: str, max_messages: int = 10) -> List[Dict]:
        """
        Get conversation history.

        Args:
            session_id: Session ID
            max_messages: Max recent messages to return

        Returns:
            List of messages (most recent first)
        """
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session["messages"]
        return messages[-max_messages:]  # Last N messages

    def clear_session(self, session_id: str):
        """Delete session."""
        key = f"chat:session:{session_id}"
        self.redis.delete(key)

    def get_active_sessions(self, user_id: str = None) -> List[str]:
        """List all active sessions (optionally for a user)."""
        pattern = "chat:session:*"
        session_ids = []

        for key in self.redis.scan_iter(match=pattern):
            session_id = key.split(":")[-1]

            if user_id:
                session = self.get_session(session_id)
                if session and session.get("user_id") == user_id:
                    session_ids.append(session_id)
            else:
                session_ids.append(session_id)

        return session_ids


# ===== OPTION 2: PostgreSQL-based Session Store =====


class PostgresChatSessionStore:
    """
    PostgreSQL-based chat session storage.

    Pros:
    - Persistent (survives restarts)
    - Can query/analyze conversations
    - ACID guarantees
    - Better for compliance/audit

    Cons:
    - Slower than Redis (~10-50ms)
    - Requires table schema
    - More storage overhead

    Best for: Production with compliance requirements
    """

    # Table schema (run once):
    """
    CREATE TABLE chat_sessions (
        session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id VARCHAR(255),
        created_at TIMESTAMP DEFAULT NOW(),
        last_activity TIMESTAMP DEFAULT NOW(),
        metadata JSONB DEFAULT '{}'::jsonb
    );
    
    CREATE TABLE chat_messages (
        id SERIAL PRIMARY KEY,
        session_id UUID REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT NOW(),
        metadata JSONB DEFAULT '{}'::jsonb
    );
    
    CREATE INDEX idx_session_messages ON chat_messages(session_id, timestamp);
    CREATE INDEX idx_session_user ON chat_sessions(user_id);
    """

    def __init__(self, db_connection_string: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        self.engine = create_engine(db_connection_string)
        self.Session = sessionmaker(bind=self.engine)

    def create_session(self, user_id: str = None) -> str:
        """Create new session in PostgreSQL."""
        from sqlalchemy import text

        with self.Session() as session:
            result = session.execute(
                text(
                    """
                    INSERT INTO chat_sessions (user_id, metadata)
                    VALUES (:user_id, :metadata)
                    RETURNING session_id
                """
                ),
                {"user_id": user_id, "metadata": json.dumps({})},
            )
            session_id = str(result.fetchone()[0])
            session.commit()

        return session_id

    def add_message(
        self, session_id: str, role: str, content: str, metadata: Dict = None
    ):
        """Add message to PostgreSQL."""
        from sqlalchemy import text

        with self.Session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO chat_messages (session_id, role, content, metadata)
                    VALUES (:session_id, :role, :content, :metadata)
                """
                ),
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "metadata": json.dumps(metadata or {}),
                },
            )

            # Update last_activity
            session.execute(
                text(
                    """
                    UPDATE chat_sessions
                    SET last_activity = NOW()
                    WHERE session_id = :session_id
                """
                ),
                {"session_id": session_id},
            )

            session.commit()

    def get_history(self, session_id: str, max_messages: int = 10) -> List[Dict]:
        """Get conversation history from PostgreSQL."""
        from sqlalchemy import text

        with self.Session() as session:
            result = session.execute(
                text(
                    """
                    SELECT role, content, timestamp, metadata
                    FROM chat_messages
                    WHERE session_id = :session_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """
                ),
                {"session_id": session_id, "limit": max_messages},
            )

            messages = []
            for row in result:
                messages.append(
                    {
                        "role": row[0],
                        "content": row[1],
                        "timestamp": row[2].isoformat(),
                        "metadata": row[3] if row[3] else {},
                    }
                )

            return list(reversed(messages))  # Oldest first


# ===== OPTION 3: Hybrid Approach (Best of Both) =====


class HybridChatSessionStore:
    """
    Hybrid: Redis for hot data, PostgreSQL for persistence.

    Strategy:
    - Write to both Redis + PostgreSQL
    - Read from Redis (fast)
    - Fallback to PostgreSQL if Redis miss
    - PostgreSQL as authoritative source

    Best for: Production with high performance + compliance
    """

    def __init__(
        self, redis_store: RedisChatSessionStore, pg_store: PostgresChatSessionStore
    ):
        self.redis = redis_store
        self.pg = pg_store

    def create_session(self, user_id: str = None) -> str:
        # Create in PostgreSQL first (authoritative)
        session_id = self.pg.create_session(user_id)

        # Cache in Redis
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
        }

        key = f"chat:session:{session_id}"
        self.redis.redis.setex(key, self.redis.session_ttl, json.dumps(session_data))

        return session_id

    def add_message(
        self, session_id: str, role: str, content: str, metadata: Dict = None
    ):
        # Write to both
        self.pg.add_message(session_id, role, content, metadata)
        self.redis.add_message(session_id, role, content, metadata)

    def get_history(self, session_id: str, max_messages: int = 10) -> List[Dict]:
        # Try Redis first (fast)
        messages = self.redis.get_history(session_id, max_messages)

        if messages:
            return messages

        # Fallback to PostgreSQL
        messages = self.pg.get_history(session_id, max_messages)

        # Backfill Redis cache
        if messages:
            session = {
                "session_id": session_id,
                "messages": messages,
                "last_activity": datetime.utcnow().isoformat(),
            }

            key = f"chat:session:{session_id}"
            self.redis.redis.setex(key, self.redis.session_ttl, json.dumps(session))

        return messages


# ===== Context Window Management =====


class ContextWindowManager:
    """
    Manage LLM context window (token limits).

    OpenAI models:
    - gpt-4o-mini: 128k tokens
    - gpt-4o: 128k tokens
    - gpt-3.5-turbo: 16k tokens

    Strategies:
    1. Sliding window: Keep last N messages
    2. Summary: Summarize old messages
    3. Semantic: Keep most relevant messages
    """

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens

    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation.
        Rule of thumb: 1 token ≈ 4 characters (English)
        For Vietnamese: ~1 token ≈ 2-3 characters
        """
        return len(text) // 3  # Conservative estimate

    def sliding_window(
        self, messages: List[Dict], max_messages: int = 10
    ) -> List[Dict]:
        """Keep only last N messages."""
        return messages[-max_messages:]

    def token_limited(
        self,
        messages: List[Dict],
        system_prompt: str = "",
        reserve_tokens: int = 1000,  # For response
    ) -> List[Dict]:
        """
        Keep messages that fit in context window.

        Args:
            messages: Full conversation history
            system_prompt: System prompt (counted in tokens)
            reserve_tokens: Tokens to reserve for response

        Returns:
            Filtered messages that fit
        """
        # Count system prompt tokens
        used_tokens = self.estimate_tokens(system_prompt) + reserve_tokens

        # Add messages from most recent, stop when limit reached
        result = []
        for message in reversed(messages):
            msg_tokens = self.estimate_tokens(message["content"])

            if used_tokens + msg_tokens > self.max_tokens:
                break

            result.insert(0, message)
            used_tokens += msg_tokens

        return result

    def summarize_old_messages(
        self,
        messages: List[Dict],
        llm,  # LLM instance for summarization
        keep_recent: int = 5,
    ) -> List[Dict]:
        """
        Summarize old messages, keep recent ones intact.

        Strategy:
        - Keep last 5 messages as-is
        - Summarize older messages into 1 summary message
        """
        if len(messages) <= keep_recent:
            return messages

        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        # Combine old messages for summarization
        old_text = "\n\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in old_messages]
        )

        # Summarize (using LLM)
        summary_prompt = f"""Tóm tắt cuộc hội thoại sau đây một cách ngắn gọn:

{old_text}

Tóm tắt:"""

        summary = llm.invoke(summary_prompt).content

        # Create summary message
        summary_msg = {
            "role": "system",
            "content": f"[Tóm tắt cuộc hội thoại trước đó]: {summary}",
            "timestamp": old_messages[0]["timestamp"],
            "metadata": {"is_summary": True},
        }

        return [summary_msg] + recent_messages


# ===== Integration with LangChain =====


def format_messages_for_langchain(messages: List[Dict]) -> List:
    """
    Convert session messages to LangChain format.

    Args:
        messages: Session messages from store

    Returns:
        List of LangChain message objects
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    langchain_messages = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        elif role == "system":
            langchain_messages.append(SystemMessage(content=content))

    return langchain_messages


# ===== Production Recommendation =====


def create_production_session_manager():
    """
    Factory function for production session manager.

    Recommended: Hybrid approach
    - Redis for speed
    - PostgreSQL for persistence
    """
    redis_store = RedisChatSessionStore(
        redis_host="localhost",
        redis_port=6379,
        redis_db=1,
        session_ttl=3600,  # 1 hour
    )

    pg_store = PostgresChatSessionStore(db_connection_string="postgresql://...")

    return HybridChatSessionStore(redis_store, pg_store)
