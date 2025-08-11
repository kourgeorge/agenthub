"""Agent file model for storing multiple files per agent."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class AgentFile(Base):
    """Model for storing individual files associated with an agent."""
    
    __tablename__ = "agent_files"
    
    # Relationships
    agent_id = Column(String(20), ForeignKey("agents.id"), nullable=False)
    
    # File Information
    file_path = Column(String(500), nullable=False)  # Relative path within agent directory
    file_name = Column(String(255), nullable=False)  # Just the filename
    file_content = Column(Text, nullable=False)  # File content as text
    file_type = Column(String(50), nullable=True)  # File extension or type
    file_size = Column(Integer, nullable=True)  # File size in bytes
    
    # Metadata
    is_main_file = Column(String(1), nullable=False, default='N')  # 'Y' if this is the main entry point file
    is_executable = Column(String(1), nullable=False, default='N')  # 'Y' if this is a Python/executable file
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    agent = relationship("Agent", back_populates="files")
    
    def __repr__(self) -> str:
        return f"<AgentFile(id={self.id}, agent_id={self.agent_id}, file_path='{self.file_path}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_content": self.file_content,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "is_main_file": self.is_main_file,
            "is_executable": self.is_executable,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 