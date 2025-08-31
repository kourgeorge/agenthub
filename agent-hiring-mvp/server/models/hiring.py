"""Hiring model for tracking agent hiring records."""

from enum import Enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, JSON, Float, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class HiringStatus(str, Enum):
    """Hiring status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"
    CANCELLING = "cancelling"
    CANCELLATION_FAILED = "cancellation_failed"


class Hiring(Base):
    """Hiring model for tracking agent hiring records."""
    
    __tablename__ = "hirings"
    
    # Relationships
    agent_id = Column(String(20), ForeignKey("agents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional for anonymous hiring
    
    # Hiring Details
    status = Column(String(20), nullable=False, default=HiringStatus.ACTIVE.value)
    hired_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # None for permanent hiring
    
    # Configuration
    config = Column(JSON, nullable=True)  # Agent-specific configuration
    state = Column(JSON, nullable=True)  # Persistent agent state data
    acp_endpoint = Column(String(500), nullable=True)  # ACP communication endpoint
    
    # Usage Tracking
    last_executed_at = Column(DateTime, nullable=True)
    
    # Billing (future)
    billing_cycle = Column(String(20), nullable=True)  # "monthly", "per_use", "lifetime"
    next_billing_date = Column(DateTime, nullable=True)
    
    # Relationships
    agent = relationship("Agent", back_populates="hirings")
    user = relationship("User", back_populates="hirings")
    executions = relationship("Execution", back_populates="hiring")
    
    def __repr__(self) -> str:
        return f"<Hiring(id={self.id}, agent_id={self.agent_id}, status='{self.status}')>" 