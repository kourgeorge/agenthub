"""User API Key model for authentication."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class UserApiKey(Base):
    """User API Key for programmatic authentication."""
    __tablename__ = "user_api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Key details
    name = Column(String(100), nullable=False)  # User-friendly name for the key
    key_hash = Column(String(255), nullable=False)  # Hashed version of the API key
    key_prefix = Column(String(8), nullable=False)  # First 8 characters for display
    
    # Permissions and status
    is_active = Column(Boolean, default=True, nullable=False)
    permissions = Column(Text, nullable=True)  # JSON string of permissions
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Optional expiration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_api_keys")
    
    def __repr__(self) -> str:
        return f"<UserApiKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired
