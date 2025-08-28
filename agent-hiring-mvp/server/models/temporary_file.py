"""Temporary file model for storing file references during agent execution."""

from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship

from .base import Base


class TemporaryFile(Base):
    """Model for storing temporary files uploaded for agent execution."""
    
    __tablename__ = "temporary_files"
    
    # Override id to use string-based UUID for better security
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File Information
    original_filename = Column(String(255), nullable=False)  # Original filename from user
    stored_filename = Column(String(255), nullable=False)  # Generated filename for storage
    file_path = Column(String(500), nullable=False)  # Full path to stored file
    file_size = Column(Integer, nullable=False)  # File size in bytes
    file_type = Column(String(100), nullable=True)  # MIME type
    file_extension = Column(String(20), nullable=True)  # File extension
    
    # Metadata
    description = Column(Text, nullable=True)  # User-provided description
    tags = Column(Text, nullable=True)  # JSON string of tags
    
    # Security and Access Control
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    access_token = Column(String(64), nullable=False, unique=True, index=True)  # For secure file access
    
    # Lifecycle Management
    expires_at = Column(DateTime, nullable=False)  # When file should be automatically deleted
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete flag
    
    # Usage Tracking
    download_count = Column(Integer, default=0, nullable=False)  # How many times accessed
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="temporary_files")
    
    def __repr__(self) -> str:
        return f"<TemporaryFile(id='{self.id}', filename='{self.original_filename}', user_id={self.user_id})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "file_extension": self.file_extension,
            "description": self.description,
            "tags": self.tags,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "download_count": self.download_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "access_url": f"/api/files/{self.id}/download?token={self.access_token}"
        }
    
    @classmethod
    def create_with_expiry(cls, **kwargs):
        """Create a temporary file with automatic expiry (default 24 hours)."""
        # Set default expiry to 24 hours from now
        if 'expires_at' not in kwargs:
            kwargs['expires_at'] = datetime.utcnow() + timedelta(hours=24)
        
        # Generate access token
        if 'access_token' not in kwargs:
            kwargs['access_token'] = uuid.uuid4().hex
        
        return cls(**kwargs)
    
    def is_expired(self) -> bool:
        """Check if file has expired."""
        return datetime.utcnow() > self.expires_at
    
    def should_auto_delete(self) -> bool:
        """Check if file should be automatically deleted."""
        return self.is_expired() or self.is_deleted
    
    def mark_accessed(self):
        """Mark file as accessed and update counters."""
        self.download_count += 1
        self.last_accessed_at = datetime.utcnow()
