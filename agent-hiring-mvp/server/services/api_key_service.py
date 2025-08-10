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
        print(f"DEBUG: ApiKeyService.create_api_key called with user_id={user_id}, name='{name}'")
        print(f"DEBUG: Database session: {db}")
        
        # Generate the API key
        api_key = ApiKeyService.generate_api_key()
        key_hash = ApiKeyService.hash_api_key(api_key)
        key_prefix = api_key[:8]
        
        print(f"DEBUG: Generated API key with prefix: {key_prefix}")
        
        # Set expiration if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create the database record
        db_api_key = UserApiKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions,
            expires_at=expires_at
        )
        
        print(f"DEBUG: Created UserApiKey object: {db_api_key}")
        print(f"DEBUG: About to add to database and commit")
        
        db.add(db_api_key)
        db.commit()
        db.refresh(db_api_key)
        
        print(f"DEBUG: Successfully committed to database, API key ID: {db_api_key.id}")
        
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
        print(f"DEBUG: ApiKeyService.get_user_api_keys called with user_id={user_id}")
        print(f"DEBUG: Database session: {db}")
        
        try:
            print("DEBUG: About to query UserApiKey table")
            result = db.query(UserApiKey).filter(
                UserApiKey.user_id == user_id
            ).order_by(UserApiKey.created_at.desc()).all()
            print(f"DEBUG: Successfully queried {len(result)} API keys")
            return result
        except Exception as e:
            print(f"DEBUG: Exception in get_user_api_keys: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
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
