"""
JWT Token Handler
Create and verify JWT access/refresh tokens
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import jwt

from src.config.auth import auth_config


class JWTHandler:
    """JWT token creation and verification"""
    
    def __init__(self):
        self.secret_key = auth_config.secret_key
        self.algorithm = auth_config.algorithm
        self.access_expire_minutes = auth_config.access_token_expire_minutes
        self.refresh_expire_days = auth_config.refresh_token_expire_days
    
    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        role: str = "user",
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create JWT access token
        
        Args:
            user_id: User UUID
            email: User email
            role: User role (default "user")
            extra_claims: Additional claims to include
            
        Returns:
            Encoded JWT token string
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_expire_minutes)
        
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_id: UUID) -> str:
        """
        Create JWT refresh token
        
        Args:
            user_id: User UUID
            
        Returns:
            Encoded JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=self.refresh_expire_days)
        
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, expected_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token string
            expected_type: Expected token type ("access" or "refresh")
            
        Returns:
            Decoded payload dict, or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Verify token type
            if payload.get("type") != expected_type:
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_id_from_token(self, token: str) -> Optional[UUID]:
        """
        Extract user ID from token
        
        Args:
            token: JWT token string
            
        Returns:
            User UUID or None if invalid
        """
        payload = self.verify_token(token)
        if payload and "sub" in payload:
            try:
                return UUID(payload["sub"])
            except ValueError:
                return None
        return None
    
    def create_token_pair(
        self,
        user_id: UUID,
        email: str,
        role: str = "user"
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens
        
        Args:
            user_id: User UUID
            email: User email
            role: User role
            
        Returns:
            Dict with access_token and refresh_token
        """
        return {
            "access_token": self.create_access_token(user_id, email, role),
            "refresh_token": self.create_refresh_token(user_id),
            "token_type": "bearer",
            "expires_in": self.access_expire_minutes * 60,  # in seconds
        }


# Global JWT handler instance
jwt_handler = JWTHandler()
