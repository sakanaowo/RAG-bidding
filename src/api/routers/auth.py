"""
Authentication Router
Endpoints for user registration, login, and account management
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.models.base import get_db
from src.models.users import User
from src.auth.dependencies import get_current_user, get_current_active_user
from src.config.auth import auth_config
from src.api.schemas.auth_schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    ChangePasswordRequest,
    RefreshTokenRequest,
    UpdateProfileRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
    MessageResponse,
    OAuthProvider,
)
from src.api.services.auth_service import auth_service


router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# LOCAL AUTHENTICATION ENDPOINTS
# =============================================================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    
    - **email**: Valid email address (must be unique)
    - **password**: Min 8 chars with uppercase, lowercase, and digit
    - **full_name**: Optional display name
    """
    user, error = auth_service.register_user(
        db=db,
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    # Auto-login after registration
    user, tokens, _ = auth_service.login_user(
        db=db,
        email=request.email,
        password=request.password
    )
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(**tokens)
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password
    
    Returns access and refresh tokens
    """
    user, tokens, error = auth_service.login_user(
        db=db,
        email=request.email,
        password=request.password
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(**tokens)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    tokens, error = auth_service.refresh_tokens(
        db=db,
        refresh_token=request.refresh_token
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return TokenResponse(**tokens)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user
    
    Note: JWT tokens are stateless, so this endpoint mainly serves
    as a signal to the client to clear tokens. For true logout,
    implement token blacklisting or use short-lived tokens.
    """
    # In a production system, you might want to:
    # 1. Add the token to a blacklist (Redis)
    # 2. Clear any server-side sessions
    # For now, we just return success
    
    return MessageResponse(
        message="Successfully logged out",
        success=True
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user's information
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    
    Only provided fields will be updated
    """
    updated_user = auth_service.update_profile(
        db=db,
        user=current_user,
        full_name=request.full_name,
        avatar_url=request.avatar_url,
        preferred_rag_mode=request.preferred_rag_mode,
        preferred_categories=request.preferred_categories
    )
    
    return UserResponse.model_validate(updated_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password
    """
    success, error = auth_service.change_password(
        db=db,
        user=current_user,
        current_password=request.current_password,
        new_password=request.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return MessageResponse(
        message="Password changed successfully",
        success=True
    )


# =============================================================================
# OAUTH ENDPOINTS
# =============================================================================

@router.get("/oauth/providers")
async def list_oauth_providers():
    """
    List available OAuth providers and their status
    """
    return {
        "providers": [
            {
                "name": "google",
                "enabled": auth_config.is_oauth_configured("google"),
                "login_url": "/api/auth/oauth/google" if auth_config.is_oauth_configured("google") else None
            },
            {
                "name": "github",
                "enabled": auth_config.is_oauth_configured("github"),
                "login_url": "/api/auth/oauth/github" if auth_config.is_oauth_configured("github") else None
            }
        ]
    }


@router.get("/oauth/google")
async def google_oauth_redirect():
    """
    Redirect to Google OAuth for authentication
    """
    from src.api.services.oauth_service import google_oauth_service
    from fastapi.responses import RedirectResponse
    import secrets
    
    if not google_oauth_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    # TODO: Store state in session/redis for verification
    
    auth_url = google_oauth_service.get_authorization_url(state=state)
    return RedirectResponse(url=auth_url)


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback
    
    - Exchange code for tokens
    - Get user info from Google
    - Create or update user in database
    - Generate JWT tokens
    - Redirect to frontend with tokens
    """
    from src.api.services.oauth_service import google_oauth_service
    from src.models.repositories import UserRepository
    from src.auth.jwt_handler import jwt_handler
    from fastapi.responses import RedirectResponse
    import logging
    
    logger = logging.getLogger(__name__)
    
    if error:
        logger.error(f"OAuth error: {error}")
        return RedirectResponse(url=f"{auth_config.frontend_url}/login?error={error}")
    
    try:
        # Authenticate with Google
        result = await google_oauth_service.authenticate(code)
        user_info = result["user_info"]
        
        logger.info(f"Google OAuth user: {user_info.get('email')}")
        
        # Find or create user
        email = user_info.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        user = UserRepository.get_by_email(db, email)
        
        if not user:
            # Create new user
            user = UserRepository.create(
                db=db,
                email=email,
                password_hash="",  # OAuth users don't have password
                full_name=user_info.get("name"),
                oauth_provider="google",
                oauth_id=user_info.get("sub"),
                is_active=True,  # Trust Google verified emails
                is_verified=True,  # Google already verified email
            )
            logger.info(f"Created new OAuth user: {email}")
        else:
            # Update existing user with OAuth info if not set
            if not user.oauth_provider:
                user.oauth_provider = "google"
                user.oauth_id = user_info.get("sub")
            if user_info.get("name") and not user.full_name:
                user.full_name = user_info.get("name")
            if not user.is_verified:
                user.is_verified = True  # Google already verified email
            db.commit()
            logger.info(f"Updated existing user with OAuth: {email}")
        
        # Generate JWT tokens
        access_token = jwt_handler.create_access_token(user.id, user.email, user.role or "user")
        refresh_token = jwt_handler.create_refresh_token(user.id)
        
        # Redirect to frontend with token
        redirect_url = f"{auth_config.frontend_url}/auth/callback?access_token={access_token}&refresh_token={refresh_token}"
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"{auth_config.frontend_url}/login?error=oauth_failed")


@router.get("/oauth/{provider}")
async def oauth_redirect(provider: str):
    """
    Redirect to OAuth provider for authentication
    
    Currently only Google is supported
    """
    if provider == "google":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/api/auth/oauth/google")
    
    if provider not in [p.value for p in OAuthProvider]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth flow for '{provider}' is not yet implemented. Only Google is currently supported."
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback_generic(
    provider: str,
    code: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from any provider
    
    Currently redirects to provider-specific handlers
    """
    if provider == "google":
        return await google_oauth_callback(code=code, state=state, db=db)
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"OAuth callback for '{provider}' is not yet implemented"
    )


# =============================================================================
# ADMIN ENDPOINTS (Protected)
# =============================================================================

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID (admin only or self)
    """
    from uuid import UUID
    from src.models.repositories import UserRepository
    
    try:
        target_user_id = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    
    # Allow access to own profile or admin access
    if current_user.id != target_user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    user = UserRepository.get_by_id(db, target_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.model_validate(user)
