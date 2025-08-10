"""User model for user accounts."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """User model for user accounts."""
    
    __tablename__ = "users"
    
    # Basic Information
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    
    # Authentication
    password = Column(String(255), nullable=False)  # Hashed password
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Profile
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    
    # Preferences
    preferences = Column(JSON, nullable=True)  # User preferences
    
    # Timestamps
    last_login_at = Column(DateTime, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    hirings = relationship("Hiring", back_populates="user")
    executions = relationship("Execution", back_populates="user")
    budget = relationship("UserBudget", back_populates="user", uselist=False)
    api_keys = relationship("ApiKey", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>" 