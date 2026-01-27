"""
Authentication Pydantic Schemas
Request/Response models for auth endpoints
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class OAuthProvider(str, Enum):
    """Supported OAuth providers (for future)"""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class UserRole(str, Enum):
    """User roles"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class UserRegisterRequest(BaseModel):
    """Request body for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, max_length=255, description="User's full name")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "test@example.com",
                    "password": "Test1234!",
                    "full_name": "Test User"
                }
            ]
        }
    }
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseModel):
    """Request body for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(False, description="Extend token expiration")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "test@example.com",
                    "password": "Test1234!",
                    "remember_me": False
                }
            ]
        }
    }


class ChangePasswordRequest(BaseModel):
    """Request body for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")


class UpdateProfileRequest(BaseModel):
    """Request body for profile update"""
    full_name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=500)
    preferred_rag_mode: Optional[str] = Field(None, pattern="^(fast|balanced|quality)$")
    preferred_categories: Optional[List[str]] = None


# =============================================================================
# RESPONSE SCHEMAS
# =============================================================================

class TokenResponse(BaseModel):
    """Response with JWT tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration in seconds")


class UserResponse(BaseModel):
    """User information response"""
    id: UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False
    oauth_provider: Optional[str] = None
    preferred_rag_mode: Optional[str] = None
    preferred_categories: Optional[List[str]] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Combined auth response with user and tokens"""
    user: UserResponse
    tokens: TokenResponse


class MessageResponse(BaseModel):
    """Simple message response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None


# =============================================================================
# OAUTH SCHEMAS (Future-ready)
# =============================================================================

class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters"""
    code: str = Field(..., description="Authorization code from OAuth provider")
    state: Optional[str] = Field(None, description="State parameter for CSRF protection")


class OAuthUserInfo(BaseModel):
    """User info from OAuth provider"""
    provider: OAuthProvider
    oauth_id: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    email_verified: bool = False
