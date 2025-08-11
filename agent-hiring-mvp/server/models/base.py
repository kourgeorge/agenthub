"""Base model for SQLAlchemy models."""

import re
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    
    # Support both integer and string IDs
    id = Column(Integer, primary_key=True, index=True)
    # For models that need string IDs (like agents), they can override this
    # agent_id = Column(String(20), primary_key=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @classmethod
    def generate_abbreviated_id(cls, name: str, category: str = "general") -> str:
        """Generate an abbreviated ID from name and category.
        
        Args:
            name: The full name to abbreviate
            category: The category (optional, defaults to "general")
            
        Returns:
            A unique abbreviated ID like "SRAa1b" or "GENe5f"
        """
        words = name.split()
        
        if len(words) == 1:
            # Single word: take first 8 chars + suffix
            base = words[0][:8].upper()
        else:
            # Multiple words: take first letter of each + suffix
            base = ''.join(word[0].upper() for word in words)
        
        # Add category prefix if it's not "general"
        if category and category.lower() != "general":
            cat_prefix = category[:2].upper()
            base = f"{cat_prefix}{base}"
        
        # Add random suffix for uniqueness
        suffix = uuid.uuid4().hex[:3]
        return f"{base}{suffix}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        } 