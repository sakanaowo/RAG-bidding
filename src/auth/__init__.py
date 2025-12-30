"""
Authentication Module - Schema v3
Provides password hashing, JWT tokens, and OAuth utilities
"""

from .password import PasswordHasher, password_hasher
from .jwt_handler import JWTHandler, jwt_handler
from .dependencies import get_current_user, get_current_active_user, get_optional_user

__all__ = [
    "PasswordHasher",
    "password_hasher",
    "JWTHandler", 
    "jwt_handler",
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
]
