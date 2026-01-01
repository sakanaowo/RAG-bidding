"""
Password Hashing Utilities
Uses bcrypt for secure password hashing
"""

import bcrypt
import re
from typing import Tuple

from src.config.auth import auth_config


class PasswordHasher:
    """Password hashing and validation utilities"""
    
    def __init__(self, rounds: int = 12):
        """
        Initialize password hasher
        
        Args:
            rounds: bcrypt work factor (default 12, higher = slower but more secure)
        """
        self.rounds = rounds
    
    def hash(self, password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=self.rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify(self, password: str, hashed: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Plain text password to verify
            hashed: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed.encode('utf-8')
            )
        except Exception:
            return False
    
    def validate_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength against policy
        
        Args:
            password: Plain text password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []
        
        if len(password) < auth_config.password_min_length:
            errors.append(f"Password must be at least {auth_config.password_min_length} characters")
        
        if auth_config.password_require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if auth_config.password_require_lowercase and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if auth_config.password_require_digit and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if auth_config.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, ""


# Global password hasher instance
password_hasher = PasswordHasher()
