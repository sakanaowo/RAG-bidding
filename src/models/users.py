"""
User Model - Schema v3
Represents the users table for authentication and user management
"""

from sqlalchemy import Column, String, Boolean, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING
import uuid

from .base import Base

if TYPE_CHECKING:
    from .documents import Document
    from .conversations import Conversation
    from .messages import Message
    from .feedback import Feedback
    from .queries import Query
    from .user_metrics import UserUsageMetric


class User(Base):
    """
    User model for authentication and profile management
    
    Supports:
    - Local authentication (email/password)
    - OAuth providers (Google, GitHub, etc.)
    - Role-based access control
    - User preferences
    """

    __tablename__ = "users"

    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        comment="Primary key"
    )

    # Authentication
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email (unique)"
    )

    username = Column(
        String(100),
        nullable=True,
        comment="Display username"
    )

    password_hash = Column(
        String(255),
        nullable=True,
        comment="Bcrypt hashed password (null for OAuth users)"
    )

    full_name = Column(
        String(255),
        nullable=True,
        comment="User's full name"
    )

    # Role-based access
    role = Column(
        String(50),
        default="user",
        nullable=True,
        comment="Role: user, admin, moderator"
    )

    # OAuth support
    oauth_provider = Column(
        String(50),
        nullable=True,
        comment="OAuth provider: google, github, etc."
    )

    oauth_id = Column(
        String(255),
        nullable=True,
        comment="OAuth provider's user ID"
    )

    # User preferences (theme, language, default RAG mode, etc.)
    preferences = Column(
        JSONB,
        default={},
        server_default="{}",
        nullable=True,
        comment="User preferences as JSON"
    )

    # Account status
    is_active = Column(
        Boolean,
        default=True,
        nullable=True,
        comment="Whether account is active"
    )

    is_verified = Column(
        Boolean,
        default=False,
        nullable=True,
        comment="Whether email is verified"
    )

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=True,
        comment="Account creation timestamp"
    )

    updated_at = Column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
        comment="Last update timestamp"
    )

    deleted_at = Column(
        TIMESTAMP(timezone=False),
        nullable=True,
        comment="Soft delete timestamp"
    )

    # Relationships
    documents = relationship(
        "Document",
        back_populates="uploader",
        foreign_keys="Document.uploaded_by"
    )
    
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    messages = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    queries = relationship(
        "Query",
        back_populates="user"
    )
    
    usage_metrics = relationship(
        "UserUsageMetric",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_oauth", "oauth_provider", "oauth_id"),
        {"comment": "User accounts table (v3)"},
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    def to_dict(self, include_sensitive: bool = False):
        """Convert to dictionary for JSON serialization"""
        data = {
            "id": str(self.id),
            "email": self.email,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "oauth_provider": self.oauth_provider,
            "preferences": self.preferences,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data["oauth_id"] = self.oauth_id
            
        return data
