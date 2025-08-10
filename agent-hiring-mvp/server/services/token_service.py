"""Token service for managing password reset and email verification tokens."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets

class TokenService:
    """Service for managing temporary tokens."""
    
    # In-memory storage for tokens (in production, use Redis or database)
    _reset_tokens: Dict[str, Dict[str, Any]] = {}
    _verification_tokens: Dict[str, Dict[str, Any]] = {}
    _blacklisted_tokens: set = set()  # Add blacklist for invalidated tokens
    
    @classmethod
    def store_reset_token(cls, email: str, user_id: int, expires_in_days: int = 1) -> str:
        """Store a password reset token for an email."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        cls._reset_tokens[token] = {
            "email": email,
            "user_id": user_id,
            "expires_at": expires_at,
            "used": False
        }
        
        return token
    
    @classmethod
    def store_verification_token(cls, email: str, user_id: int, expires_in_days: int = 7) -> str:
        """Store an email verification token for an email."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        cls._verification_tokens[token] = {
            "email": email,
            "user_id": user_id,
            "expires_at": expires_at,
            "used": False
        }
        
        return token
    
    @classmethod
    def validate_reset_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Validate a password reset token."""
        if token in cls._blacklisted_tokens:  # Check if token is blacklisted
            return None
            
        token_data = cls._reset_tokens.get(token)
        if not token_data:
            return None
        
        if token_data["used"]:
            return None
        
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            # Clean up expired token
            cls._reset_tokens.pop(token, None)
            return None
        
        return token_data
    
    @classmethod
    def validate_verification_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Validate an email verification token."""
        if token in cls._blacklisted_tokens:  # Check if token is blacklisted
            return None
            
        token_data = cls._verification_tokens.get(token)
        if not token_data:
            return None
        
        if token_data["used"]:
            return None
        
        if datetime.now(timezone.utc) > token_data["expires_at"]:
            # Clean up expired token
            cls._verification_tokens.pop(token, None)
            return None
        
        return token_data
    
    @classmethod
    def mark_reset_token_used(cls, token: str) -> bool:
        """Mark a password reset token as used."""
        if token in cls._reset_tokens:
            cls._reset_tokens[token]["used"] = True
            return True
        return False
    
    @classmethod
    def mark_verification_token_used(cls, token: str) -> bool:
        """Mark an email verification token as used."""
        if token in cls._verification_tokens:
            cls._verification_tokens[token]["used"] = True
            return True
        return False
    
    @classmethod
    def cleanup_expired_tokens(cls) -> None:
        """Clean up expired tokens from memory."""
        now = datetime.now(timezone.utc)
        
        # Clean up expired reset tokens
        expired_reset = [
            token for token, data in cls._reset_tokens.items()
            if now > data["expires_at"]
        ]
        for token in expired_reset:
            cls._reset_tokens.pop(token, None)
        
        # Clean up expired verification tokens
        expired_verification = [
            token for token, data in cls._verification_tokens.items()
            if now > data["expires_at"]
        ]
        for token in expired_verification:
            cls._verification_tokens.pop(token, None)
    
    @classmethod
    def blacklist_token(cls, token: str) -> None:
        """Add a token to the blacklist to prevent its reuse."""
        cls._blacklisted_tokens.add(token)
    
    @classmethod
    def is_token_blacklisted(cls, token: str) -> bool:
        """Check if a token is blacklisted."""
        return token in cls._blacklisted_tokens
    
    @classmethod
    def cleanup_blacklist(cls, max_age_hours: int = 24) -> None:
        """Clean up old blacklisted tokens to prevent memory issues."""
        # In a production system, you might want to implement this
        # to prevent the blacklist from growing indefinitely
        # For now, we'll keep it simple and just clear the entire blacklist
        # In production, you'd want to track when tokens were blacklisted
        # and remove only the old ones
        cls._blacklisted_tokens.clear()
