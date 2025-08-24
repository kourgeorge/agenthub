"""Permission model for defining system permissions."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship

from .base import Base


class Permission(Base):
    """Model for defining individual system permissions."""
    
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "agent:create", "admin:billing:view"
    description = Column(Text, nullable=True)
    resource = Column(String(50), nullable=False, index=True)  # e.g., "agent", "billing", "admin"
    action = Column(String(50), nullable=False, index=True)  # e.g., "create", "read", "update", "delete"
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_permission = Column(Boolean, default=False, nullable=False)  # Prevents deletion of system permissions
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}', resource='{self.resource}', action='{self.action}')>"
    
    @property
    def full_name(self) -> str:
        """Get the full permission name in format resource:action."""
        return f"{self.resource}:{self.action}"
    
    @classmethod
    def parse_permission_name(cls, permission_name: str) -> tuple[str, str]:
        """Parse a permission name into resource and action parts."""
        if ':' not in permission_name:
            raise ValueError(f"Invalid permission format: {permission_name}")
        
        parts = permission_name.split(':', 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid permission format: {permission_name}")
        
        return parts[0], parts[1]
