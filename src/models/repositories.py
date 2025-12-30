"""
Database Query Helper Functions - Schema v3
Reusable database operations for all models
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import UUID
import hashlib

from .documents import Document
from .users import User
from .conversations import Conversation
from .messages import Message
from .document_chunks import DocumentChunk
from .citations import Citation
from .feedback import Feedback
from .queries import Query
from .user_metrics import UserUsageMetric


# =============================================================================
# DOCUMENT REPOSITORY
# =============================================================================

class DocumentRepository:
    """Repository pattern for Document operations"""

    @staticmethod
    def get_by_id(db: Session, document_id: str) -> Optional[Document]:
        """Get document by document_id"""
        return db.query(Document).filter(Document.document_id == document_id).first()

    @staticmethod
    def get_by_uuid(db: Session, uuid: UUID) -> Optional[Document]:
        """Get document by UUID"""
        return db.query(Document).filter(Document.id == uuid).first()

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        category: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[Document]:
        """Get documents with filters and pagination"""
        query = db.query(Document)

        if status:
            query = query.filter(Document.status == status)
        if category:
            query = query.filter(Document.category == category)
        if document_type:
            query = query.filter(Document.document_type == document_type)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, **kwargs) -> Document:
        """Create new document"""
        doc = Document(**kwargs)
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def update(db: Session, document_id: str, **kwargs) -> Optional[Document]:
        """Update document"""
        doc = DocumentRepository.get_by_id(db, document_id)
        if not doc:
            return None

        for key, value in kwargs.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def delete(db: Session, document_id: str, soft: bool = True) -> bool:
        """Delete document (soft or hard)"""
        doc = DocumentRepository.get_by_id(db, document_id)
        if not doc:
            return False

        if soft:
            doc.status = "deleted"
            db.commit()
        else:
            db.delete(doc)
            db.commit()

        return True

    @staticmethod
    def get_stats(db: Session) -> Dict[str, Any]:
        """Get document statistics"""
        total = db.query(func.count(Document.id)).scalar()

        by_type = (
            db.query(Document.document_type, func.count(Document.id))
            .group_by(Document.document_type)
            .all()
        )

        by_category = (
            db.query(Document.category, func.count(Document.id))
            .group_by(Document.category)
            .all()
        )

        by_status = (
            db.query(Document.status, func.count(Document.id))
            .group_by(Document.status)
            .all()
        )

        return {
            "total_documents": total,
            "by_type": dict(by_type),
            "by_category": dict(by_category),
            "by_status": dict(by_status),
        }

    @staticmethod
    def search(db: Session, search_term: str, limit: int = 20) -> List[Document]:
        """Search documents by name (case-insensitive)"""
        return (
            db.query(Document)
            .filter(Document.document_name.ilike(f"%{search_term}%"))
            .limit(limit)
            .all()
        )


# =============================================================================
# USER REPOSITORY
# =============================================================================

class UserRepository:
    """Repository pattern for User operations"""

    @staticmethod
    def get_by_id(db: Session, user_id: UUID) -> Optional[User]:
        """Get user by UUID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_oauth(db: Session, provider: str, oauth_id: str) -> Optional[User]:
        """Get user by OAuth provider and ID"""
        return db.query(User).filter(
            and_(User.oauth_provider == provider, User.oauth_id == oauth_id)
        ).first()

    @staticmethod
    def create(
        db: Session,
        email: str,
        password_hash: Optional[str] = None,
        **kwargs
    ) -> User:
        """Create new user"""
        user = User(email=email, password_hash=password_hash, **kwargs)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update(db: Session, user_id: UUID, **kwargs) -> Optional[User]:
        """Update user"""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def soft_delete(db: Session, user_id: UUID) -> bool:
        """Soft delete user"""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False

        user.deleted_at = datetime.utcnow()
        user.is_active = False
        db.commit()
        return True

    @staticmethod
    def verify_email(db: Session, user_id: UUID) -> bool:
        """Mark user email as verified"""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return False

        user.is_verified = True
        db.commit()
        return True


# =============================================================================
# CONVERSATION REPOSITORY
# =============================================================================

class ConversationRepository:
    """Repository pattern for Conversation operations"""

    @staticmethod
    def get_by_id(db: Session, conversation_id: UUID) -> Optional[Conversation]:
        """Get conversation by UUID"""
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def get_user_conversations(
        db: Session,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        include_deleted: bool = False
    ) -> List[Conversation]:
        """Get all conversations for a user"""
        query = db.query(Conversation).filter(Conversation.user_id == user_id)

        if not include_deleted:
            query = query.filter(Conversation.deleted_at.is_(None))

        return query.order_by(desc(Conversation.last_message_at)).offset(skip).limit(limit).all()

    @staticmethod
    def create(
        db: Session,
        user_id: UUID,
        title: Optional[str] = None,
        rag_mode: str = "balanced",
        **kwargs
    ) -> Conversation:
        """Create new conversation"""
        conversation = Conversation(
            user_id=user_id,
            title=title,
            rag_mode=rag_mode,
            **kwargs
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    @staticmethod
    def update_last_message(db: Session, conversation_id: UUID) -> None:
        """Update last_message_at and increment message_count"""
        conversation = ConversationRepository.get_by_id(db, conversation_id)
        if conversation:
            conversation.last_message_at = datetime.utcnow()
            conversation.message_count = (conversation.message_count or 0) + 1
            db.commit()

    @staticmethod
    def update_usage(
        db: Session,
        conversation_id: UUID,
        tokens: int,
        cost_usd: float
    ) -> None:
        """Update token and cost usage"""
        conversation = ConversationRepository.get_by_id(db, conversation_id)
        if conversation:
            conversation.total_tokens = (conversation.total_tokens or 0) + tokens
            conversation.total_cost_usd = float(conversation.total_cost_usd or 0) + cost_usd
            db.commit()

    @staticmethod
    def soft_delete(db: Session, conversation_id: UUID) -> bool:
        """Soft delete conversation"""
        conversation = ConversationRepository.get_by_id(db, conversation_id)
        if not conversation:
            return False

        conversation.deleted_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def update_title(db: Session, conversation_id: UUID, title: str) -> Optional[Conversation]:
        """Update conversation title"""
        conversation = ConversationRepository.get_by_id(db, conversation_id)
        if not conversation:
            return None

        conversation.title = title
        db.commit()
        db.refresh(conversation)
        return conversation


# =============================================================================
# MESSAGE REPOSITORY
# =============================================================================

class MessageRepository:
    """Repository pattern for Message operations"""

    @staticmethod
    def get_by_id(db: Session, message_id: UUID) -> Optional[Message]:
        """Get message by UUID"""
        return db.query(Message).filter(Message.id == message_id).first()

    @staticmethod
    def get_conversation_messages(
        db: Session,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get all messages in a conversation"""
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def add_message(
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        sources: Optional[Dict] = None,
        processing_time_ms: Optional[int] = None,
        tokens_total: Optional[int] = None
    ) -> Message:
        """Add a message to conversation"""
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=role,
            content=content,
            sources=sources,
            processing_time_ms=processing_time_ms,
            tokens_total=tokens_total
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        # Update conversation last_message_at
        ConversationRepository.update_last_message(db, conversation_id)

        return message

    @staticmethod
    def update_feedback_rating(db: Session, message_id: UUID, rating: int) -> bool:
        """Update quick feedback rating on message"""
        message = MessageRepository.get_by_id(db, message_id)
        if not message:
            return False

        message.feedback_rating = rating
        db.commit()
        return True


# =============================================================================
# DOCUMENT CHUNK REPOSITORY
# =============================================================================

class DocumentChunkRepository:
    """Repository pattern for DocumentChunk operations"""

    @staticmethod
    def get_by_id(db: Session, chunk_id: UUID) -> Optional[DocumentChunk]:
        """Get chunk by UUID"""
        return db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()

    @staticmethod
    def get_by_chunk_id(db: Session, chunk_id: str) -> Optional[DocumentChunk]:
        """Get chunk by string chunk_id"""
        return db.query(DocumentChunk).filter(DocumentChunk.chunk_id == chunk_id).first()

    @staticmethod
    def get_by_document(db: Session, document_id: UUID) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        return (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    @staticmethod
    def create_batch(
        db: Session,
        document_id: UUID,
        chunks: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Create multiple chunks for a document"""
        chunk_records = []
        for i, chunk_data in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_id=chunk_data.get("chunk_id", f"{document_id}_{i}"),
                content=chunk_data["content"],
                chunk_index=chunk_data.get("chunk_index", i),
                section_title=chunk_data.get("section_title"),
                hierarchy_path=chunk_data.get("hierarchy_path"),
                keywords=chunk_data.get("keywords"),
                concepts=chunk_data.get("concepts"),
                entities=chunk_data.get("entities"),
                char_count=len(chunk_data["content"]),
                has_table=chunk_data.get("has_table", False),
                has_list=chunk_data.get("has_list", False),
            )
            db.add(chunk)
            chunk_records.append(chunk)

        db.commit()
        return chunk_records

    @staticmethod
    def increment_retrieval_count(db: Session, chunk_ids: List[UUID]) -> None:
        """Increment retrieval count for chunks"""
        db.query(DocumentChunk).filter(
            DocumentChunk.id.in_(chunk_ids)
        ).update(
            {DocumentChunk.retrieval_count: DocumentChunk.retrieval_count + 1},
            synchronize_session=False
        )
        db.commit()

    @staticmethod
    def get_most_retrieved(db: Session, limit: int = 10) -> List[DocumentChunk]:
        """Get most frequently retrieved chunks"""
        return (
            db.query(DocumentChunk)
            .order_by(desc(DocumentChunk.retrieval_count))
            .limit(limit)
            .all()
        )


# =============================================================================
# CITATION REPOSITORY
# =============================================================================

class CitationRepository:
    """Repository pattern for Citation operations"""

    @staticmethod
    def create(
        db: Session,
        message_id: UUID,
        document_id: UUID,
        chunk_id: UUID,
        citation_number: int,
        citation_text: Optional[str] = None,
        relevance_score: Optional[float] = None
    ) -> Citation:
        """Create a citation"""
        citation = Citation(
            message_id=message_id,
            document_id=document_id,
            chunk_id=chunk_id,
            citation_number=citation_number,
            citation_text=citation_text,
            relevance_score=relevance_score
        )
        db.add(citation)
        db.commit()
        db.refresh(citation)
        return citation

    @staticmethod
    def get_message_citations(db: Session, message_id: UUID) -> List[Citation]:
        """Get all citations for a message"""
        return (
            db.query(Citation)
            .filter(Citation.message_id == message_id)
            .order_by(Citation.citation_number)
            .all()
        )

    @staticmethod
    def create_batch(
        db: Session,
        message_id: UUID,
        citations: List[Dict[str, Any]]
    ) -> List[Citation]:
        """Create multiple citations for a message"""
        citation_records = []
        for i, cit_data in enumerate(citations):
            citation = Citation(
                message_id=message_id,
                document_id=cit_data["document_id"],
                chunk_id=cit_data["chunk_id"],
                citation_number=cit_data.get("citation_number", i + 1),
                citation_text=cit_data.get("citation_text"),
                relevance_score=cit_data.get("relevance_score")
            )
            db.add(citation)
            citation_records.append(citation)

        db.commit()
        return citation_records


# =============================================================================
# FEEDBACK REPOSITORY
# =============================================================================

class FeedbackRepository:
    """Repository pattern for Feedback operations"""

    @staticmethod
    def create(
        db: Session,
        user_id: UUID,
        message_id: UUID,
        rating: int,
        feedback_type: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Feedback:
        """Create feedback"""
        feedback = Feedback(
            user_id=user_id,
            message_id=message_id,
            rating=rating,
            feedback_type=feedback_type,
            comment=comment
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback

    @staticmethod
    def get_message_feedback(db: Session, message_id: UUID) -> List[Feedback]:
        """Get all feedback for a message"""
        return db.query(Feedback).filter(Feedback.message_id == message_id).all()

    @staticmethod
    def get_user_feedback(db: Session, user_id: UUID, limit: int = 50) -> List[Feedback]:
        """Get feedback from a user"""
        return (
            db.query(Feedback)
            .filter(Feedback.user_id == user_id)
            .order_by(desc(Feedback.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_feedback_stats(db: Session) -> Dict[str, Any]:
        """Get feedback statistics"""
        total = db.query(func.count(Feedback.id)).scalar()
        avg_rating = db.query(func.avg(Feedback.rating)).scalar()

        by_type = (
            db.query(Feedback.feedback_type, func.count(Feedback.id))
            .group_by(Feedback.feedback_type)
            .all()
        )

        rating_distribution = (
            db.query(Feedback.rating, func.count(Feedback.id))
            .group_by(Feedback.rating)
            .all()
        )

        return {
            "total_feedback": total,
            "average_rating": float(avg_rating) if avg_rating else None,
            "by_type": dict(by_type),
            "rating_distribution": dict(rating_distribution)
        }


# =============================================================================
# QUERY REPOSITORY
# =============================================================================

class QueryRepository:
    """Repository pattern for Query analytics"""

    @staticmethod
    def log_query(
        db: Session,
        query_text: str,
        user_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
        rag_mode: Optional[str] = None,
        categories_searched: Optional[List[str]] = None,
        retrieval_count: Optional[int] = None,
        total_latency_ms: Optional[int] = None,
        tokens_total: Optional[int] = None,
        estimated_cost_usd: Optional[float] = None
    ) -> Query:
        """Log a query for analytics"""
        # Generate query hash for cache lookup
        query_hash = hashlib.sha256(query_text.encode()).hexdigest()

        query = Query(
            query_text=query_text,
            query_hash=query_hash,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            rag_mode=rag_mode,
            categories_searched=categories_searched,
            retrieval_count=retrieval_count,
            total_latency_ms=total_latency_ms,
            tokens_total=tokens_total,
            estimated_cost_usd=estimated_cost_usd
        )
        db.add(query)
        db.commit()
        db.refresh(query)
        return query

    @staticmethod
    def get_by_hash(db: Session, query_hash: str) -> Optional[Query]:
        """Get query by hash (for cache lookup)"""
        return db.query(Query).filter(Query.query_hash == query_hash).first()

    @staticmethod
    def get_user_queries(
        db: Session,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50
    ) -> List[Query]:
        """Get queries by user"""
        return (
            db.query(Query)
            .filter(Query.user_id == user_id)
            .order_by(desc(Query.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_popular_queries(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most common queries"""
        results = (
            db.query(Query.query_hash, Query.query_text, func.count(Query.id).label("count"))
            .group_by(Query.query_hash, Query.query_text)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )
        return [{"query_text": r.query_text, "count": r.count} for r in results]

    @staticmethod
    def get_query_stats(db: Session) -> Dict[str, Any]:
        """Get query statistics"""
        total = db.query(func.count(Query.id)).scalar()
        avg_latency = db.query(func.avg(Query.total_latency_ms)).scalar()
        total_cost = db.query(func.sum(Query.estimated_cost_usd)).scalar()

        by_mode = (
            db.query(Query.rag_mode, func.count(Query.id))
            .group_by(Query.rag_mode)
            .all()
        )

        return {
            "total_queries": total,
            "avg_latency_ms": float(avg_latency) if avg_latency else None,
            "total_cost_usd": float(total_cost) if total_cost else 0,
            "by_mode": dict(by_mode)
        }


# =============================================================================
# USER USAGE METRIC REPOSITORY
# =============================================================================

class UserUsageMetricRepository:
    """Repository pattern for UserUsageMetric operations"""

    @staticmethod
    def get_or_create_today(db: Session, user_id: UUID) -> UserUsageMetric:
        """Get or create today's metric for user"""
        today = date.today()
        metric = db.query(UserUsageMetric).filter(
            and_(UserUsageMetric.user_id == user_id, UserUsageMetric.date == today)
        ).first()

        if not metric:
            metric = UserUsageMetric(user_id=user_id, date=today)
            db.add(metric)
            db.commit()
            db.refresh(metric)

        return metric

    @staticmethod
    def increment_usage(
        db: Session,
        user_id: UUID,
        queries: int = 0,
        messages: int = 0,
        tokens: int = 0,
        cost_usd: float = 0
    ) -> UserUsageMetric:
        """Increment usage metrics for today"""
        metric = UserUsageMetricRepository.get_or_create_today(db, user_id)

        metric.total_queries = (metric.total_queries or 0) + queries
        metric.total_messages = (metric.total_messages or 0) + messages
        metric.total_tokens = (metric.total_tokens or 0) + tokens
        metric.total_cost_usd = float(metric.total_cost_usd or 0) + cost_usd

        db.commit()
        db.refresh(metric)
        return metric

    @staticmethod
    def get_user_history(
        db: Session,
        user_id: UUID,
        days: int = 30
    ) -> List[UserUsageMetric]:
        """Get user usage history for last N days"""
        return (
            db.query(UserUsageMetric)
            .filter(UserUsageMetric.user_id == user_id)
            .order_by(desc(UserUsageMetric.date))
            .limit(days)
            .all()
        )

    @staticmethod
    def get_total_usage(db: Session, user_id: UUID) -> Dict[str, Any]:
        """Get total usage for user"""
        result = db.query(
            func.sum(UserUsageMetric.total_queries).label("queries"),
            func.sum(UserUsageMetric.total_messages).label("messages"),
            func.sum(UserUsageMetric.total_tokens).label("tokens"),
            func.sum(UserUsageMetric.total_cost_usd).label("cost")
        ).filter(UserUsageMetric.user_id == user_id).first()

        return {
            "total_queries": result.queries or 0,
            "total_messages": result.messages or 0,
            "total_tokens": result.tokens or 0,
            "total_cost_usd": float(result.cost) if result.cost else 0
        }
