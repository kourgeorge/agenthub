"""Execution model for tracking agent execution logs."""

from enum import Enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, JSON, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class Execution(Base):
    """Execution model for tracking agent execution logs."""
    
    __tablename__ = "executions"
    
    # Relationships
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    hiring_id = Column(Integer, ForeignKey("hirings.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Execution Details
    status = Column(String(20), nullable=False, default=ExecutionStatus.PENDING.value)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Execution duration in milliseconds
    
    # Input/Output
    input_data = Column(JSON, nullable=True)  # Input parameters
    output_data = Column(JSON, nullable=True)  # Output results
    error_message = Column(Text, nullable=True)  # Error message if failed
    
    # Resource Usage
    cpu_usage = Column(Float, nullable=True)  # CPU usage percentage
    memory_usage = Column(Float, nullable=True)  # Memory usage in MB
    disk_usage = Column(Float, nullable=True)  # Disk usage in MB
    
    # Execution Context
    execution_id = Column(String(64), nullable=False, unique=True, index=True)  # Unique execution ID
    # acp_session_id = Column(String(64), nullable=True)  # Deprecated: ACP session ID (simplified ACP no longer uses sessions)
    
    # Relationships
    agent = relationship("Agent", back_populates="executions")
    hiring = relationship("Hiring", back_populates="executions")
    user = relationship("User", back_populates="executions")
    
    def __repr__(self) -> str:
        return f"<Execution(id={self.id}, execution_id='{self.execution_id}', status='{self.status}')>" 