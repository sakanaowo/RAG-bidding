"""
Database Query Helper Functions
Reusable database operations for Documents
"""

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from typing import List, Optional, Dict, Any
from datetime import datetime

from .documents import Document


class DocumentRepository:
    """Repository pattern for Document operations"""

    @staticmethod
    def get_by_id(db: Session, document_id: str) -> Optional[Document]:
        """Get document by document_id"""
        return db.query(Document).filter(Document.document_id == document_id).first()

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
