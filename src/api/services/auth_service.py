"""
Authentication Service
Business logic for auth operations
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.users import User
from src.models.repositories import UserRepository
from src.auth.password import password_hasher
from src.auth.jwt_handler import jwt_handler


class AuthService:
    """Authentication business logic"""
    
    @staticmethod
    def register_user(
        db: Session,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> tuple[Optional[User], Optional[str]]:
        """
        Register a new user
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            full_name: Optional full name
            
        Returns:
            Tuple of (User, None) on success, (None, error_message) on failure
        """
        # Check if email already exists
        existing_user = UserRepository.get_by_email(db, email)
        if existing_user:
            return None, "Email already registered"
        
        # Validate password strength
        is_valid, error_msg = password_hasher.validate_strength(password)
        if not is_valid:
            return None, error_msg
        
        # Hash password and create user
        hashed_password = password_hasher.hash(password)
        
        user = UserRepository.create(
            db,
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            is_active=True,
            is_verified=False,  # Email verification not implemented yet
        )
        
        return user, None
    
    @staticmethod
    def login_user(
        db: Session,
        email: str,
        password: str
    ) -> tuple[Optional[User], Optional[Dict[str, Any]], Optional[str]]:
        """
        Authenticate user and create tokens
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            
        Returns:
            Tuple of (User, tokens_dict, None) on success, (None, None, error_message) on failure
        """
        # Find user by email
        user = UserRepository.get_by_email(db, email)
        if not user:
            return None, None, "Invalid email or password"
        
        # Check if user is deleted
        if user.deleted_at is not None:
            return None, None, "Account has been deleted"
        
        # Check if user is active
        if not user.is_active:
            return None, None, "Account is inactive"
        
        # Verify password
        if not user.password_hash:
            return None, None, "Account uses OAuth login"
        
        if not password_hasher.verify(password, user.password_hash):
            return None, None, "Invalid email or password"
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        db.commit()
        
        # Create tokens
        tokens = jwt_handler.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.role or "user"
        )
        
        return user, tokens, None
    
    @staticmethod
    def refresh_tokens(
        db: Session,
        refresh_token: str
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Refresh access token using refresh token
        
        Args:
            db: Database session
            refresh_token: Refresh token string
            
        Returns:
            Tuple of (tokens_dict, None) on success, (None, error_message) on failure
        """
        # Verify refresh token
        payload = jwt_handler.verify_token(refresh_token, expected_type="refresh")
        if not payload:
            return None, "Invalid or expired refresh token"
        
        # Get user
        try:
            user_id = UUID(payload["sub"])
        except (KeyError, ValueError):
            return None, "Invalid token payload"
        
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            return None, "User not found"
        
        if user.deleted_at is not None:
            return None, "Account has been deleted"
        
        if not user.is_active:
            return None, "Account is inactive"
        
        # Create new tokens
        tokens = jwt_handler.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.role or "user"
        )
        
        return tokens, None
    
    @staticmethod
    def change_password(
        db: Session,
        user: User,
        current_password: str,
        new_password: str
    ) -> tuple[bool, Optional[str]]:
        """
        Change user password
        
        Args:
            db: Database session
            user: Current user
            current_password: Current password
            new_password: New password
            
        Returns:
            Tuple of (success, error_message)
        """
        # Verify current password
        if not user.password_hash:
            return False, "Account uses OAuth login"
        
        if not password_hasher.verify(current_password, user.password_hash):
            return False, "Current password is incorrect"
        
        # Validate new password
        is_valid, error_msg = password_hasher.validate_strength(new_password)
        if not is_valid:
            return False, error_msg
        
        # Hash and update password
        user.password_hash = password_hasher.hash(new_password)
        db.commit()
        
        return True, None
    
    @staticmethod
    def update_profile(
        db: Session,
        user: User,
        **kwargs
    ) -> User:
        """
        Update user profile
        
        Args:
            db: Database session
            user: Current user
            **kwargs: Fields to update
            
        Returns:
            Updated user
        """
        allowed_fields = [
            "full_name", 
            "avatar_url", 
            "preferred_rag_mode", 
            "preferred_categories"
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return user


# Global auth service instance
auth_service = AuthService()
