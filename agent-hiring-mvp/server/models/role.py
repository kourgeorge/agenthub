"""Role model for user role management."""

from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import Column, String, Text, Boolean, JSON, DateTime, Integer
from sqlalchemy.orm import relationship

from .base import Base


class Role(Base):
    """Role model for defining user roles and their permissions."""
    
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "admin", "agent_creator", "user"
    description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=True)  # List of permission strings
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_role = Column(Boolean, default=False, nullable=False)  # Prevents deletion of system roles
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role")
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', is_active={self.is_active})>"
    
    def has_permission(self, permission: str) -> bool:
        """Check if this role has a specific permission."""
        if not self.permissions:
            return False
        return permission in self.permissions
    
    def add_permission(self, permission: str) -> None:
        """Add a permission to this role."""
        if not self.permissions:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission: str) -> None:
        """Remove a permission from this role."""
        if self.permissions and permission in self.permissions:
            self.permissions.remove(permission)
