"""
Authentication Configuration - Schema v3
JWT and OAuth settings
"""

from dataclasses import dataclass, field
import os
from typing import List


@dataclass
class AuthConfig:
    """Authentication configuration"""
    
    # JWT Settings
    secret_key: str = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY")
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Password Settings
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = False
    
    # OAuth Settings - Google
    google_client_id: str = field(
        default_factory=lambda: os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    )
    google_client_secret: str = field(
        default_factory=lambda: os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    )
    google_redirect_uri: str = field(
        default_factory=lambda: os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/oauth/google/callback")
    )
    frontend_url: str = field(
        default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:3000")
    )
    
    # OAuth Settings - GitHub (future)
    github_client_id: str = field(
        default_factory=lambda: os.getenv("GITHUB_CLIENT_ID", "")
    )
    github_client_secret: str = field(
        default_factory=lambda: os.getenv("GITHUB_CLIENT_SECRET", "")
    )
    
    # Allowed OAuth providers
    oauth_providers: List[str] = field(
        default_factory=lambda: ["google", "github"]
    )
    
    # Rate limiting
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    
    def is_oauth_configured(self, provider: str) -> bool:
        """Check if OAuth provider is configured"""
        if provider == "google":
            return bool(self.google_client_id and self.google_client_secret)
        elif provider == "github":
            return bool(self.github_client_id and self.github_client_secret)
        return False


# Global auth config instance
auth_config = AuthConfig()
