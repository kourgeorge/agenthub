"""Service for managing user API keys."""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from ..models.user_api_key import UserApiKey
from ..models.user import User


class ApiKeyService:
    """Service for managing user API keys."""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random API key."""
        # Generate 32 random bytes and encode as hex (64 characters)
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def create_api_key(
        db: Session,
        user_id: int,
        name: str,
        expires_in_days: Optional[int] = None,
        permissions: Optional[str] = None
    ) -> tuple[UserApiKey, str]:
        """Create a new API key for a user."""
        # Generate a secure random API key
        api_key = secrets.token_urlsafe(32)
        key_prefix = api_key[:8]
        
        # Hash the API key for secure storage
        key_hash = ApiKeyService.hash_api_key(api_key)
        
        # Calculate expiration date
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create the API key record
        db_api_key = UserApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            is_active=True,
            permissions=permissions or "",
            expires_at=expires_at
        )
        
        # Save to database
        db.add(db_api_key)
        db.commit()
        db.refresh(db_api_key)
        
        return db_api_key, api_key
    
    @staticmethod
    def validate_api_key(db: Session, api_key: str) -> Optional[User]:
        """Validate an API key and return the associated user."""
        if not api_key:
            return None
        
        # Hash the provided key
        key_hash = ApiKeyService.hash_api_key(api_key)
        
        # Find the API key in the database
        db_api_key = db.query(UserApiKey).filter(
            UserApiKey.key_hash == key_hash,
            UserApiKey.is_active == True
        ).first()
        
        if not db_api_key:
            return None
        
        # Check if expired
        if db_api_key.is_expired:
            return None
        
        # Update usage statistics
        db_api_key.last_used_at = datetime.now(timezone.utc)
        db_api_key.usage_count += 1
        db.commit()
        
        # Get the user
        user = db.query(User).filter(User.id == db_api_key.user_id).first()
        if not user or not user.is_active:
            return None
        
        return user
    
    @staticmethod
    def get_user_api_keys(db: Session, user_id: int) -> List[UserApiKey]:
        """Get all API keys for a user."""
        try:
            result = db.query(UserApiKey).filter(
                UserApiKey.user_id == user_id
            ).order_by(UserApiKey.created_at.desc()).all()
            return result
        except Exception as e:
            # Log error and re-raise
            raise
    
    @staticmethod
    def deactivate_api_key(db: Session, user_id: int, key_id: int) -> bool:
        """Deactivate an API key."""
        api_key = db.query(UserApiKey).filter(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user_id
        ).first()
        
        if not api_key:
            return False
        
        api_key.is_active = False
        db.commit()
        return True
    
    @staticmethod
    def delete_api_key(db: Session, user_id: int, key_id: int) -> bool:
        """Delete an API key."""
        api_key = db.query(UserApiKey).filter(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user_id
        ).first()
        
        if not api_key:
            return False
        
        db.delete(api_key)
        db.commit()
        return True
    
    @staticmethod
    def update_api_key(
        db: Session,
        user_id: int,
        key_id: int,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        permissions: Optional[str] = None
    ) -> Optional[UserApiKey]:
        """Update an API key."""
        api_key = db.query(UserApiKey).filter(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user_id
        ).first()
        
        if not api_key:
            return None
        
        if name is not None:
            api_key.name = name
        if is_active is not None:
            api_key.is_active = is_active
        if permissions is not None:
            api_key.permissions = permissions
        
        api_key.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(api_key)
        
        return api_key
