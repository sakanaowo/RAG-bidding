"""
Google OAuth Service
Handles Google OAuth 2.0 authentication flow
"""

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from typing import Optional, Dict, Any
import logging

from src.config.auth import auth_config

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleOAuthService:
    """Service for handling Google OAuth 2.0 authentication"""
    
    def __init__(self):
        self.client_id = auth_config.google_client_id
        self.client_secret = auth_config.google_client_secret
        self.redirect_uri = auth_config.google_redirect_uri
        self.frontend_url = auth_config.frontend_url
        
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        
        if state:
            params["state"] = state
            
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URL}?{query}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access tokens
        
        Args:
            code: Authorization code from Google callback
            
        Returns:
            Token response containing access_token, id_token, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise Exception(f"Token exchange failed: {response.status_code}")
                
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google
        
        Args:
            access_token: OAuth access token
            
        Returns:
            User info containing email, name, picture, etc.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.text}")
                raise Exception(f"Failed to get user info: {response.status_code}")
                
            return response.json()
    
    async def authenticate(self, code: str) -> Dict[str, Any]:
        """
        Full OAuth authentication flow
        
        Args:
            code: Authorization code from callback
            
        Returns:
            Dict with user info and tokens
        """
        # Exchange code for tokens
        tokens = await self.exchange_code_for_tokens(code)
        
        # Get user info
        user_info = await self.get_user_info(tokens["access_token"])
        
        return {
            "user_info": user_info,
            "tokens": tokens,
        }


# Singleton instance
google_oauth_service = GoogleOAuthService()
