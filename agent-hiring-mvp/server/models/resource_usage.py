"""
Database models for resource usage tracking and execution management.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base


class ExecutionResourceUsage(Base):
    """Tracks individual resource usage per execution"""
    __tablename__ = "execution_resource_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False)
    resource_type = Column(String(50), nullable=False)  # llm, vector_db, web_search
    resource_provider = Column(String(50), nullable=False)  # openai, pinecone, serper
    resource_model = Column(String(100), nullable=True)  # gpt-4, claude-3, etc.
    operation_type = Column(String(50), nullable=False)  # completion, embedding, search
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=False, default=0.0)
    request_metadata = Column(JSON, nullable=True)  # Original request details
    response_metadata = Column(JSON, nullable=True)  # Response details
    duration_ms = Column(Integer, default=0)  # Operation duration in milliseconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Note: execution relationship removed to avoid circular imports
    # It will be handled through direct queries in the UsageTracker


class ResourceConfig(Base):
    """Configuration for external resources"""
    __tablename__ = "resource_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_type = Column(String(50), nullable=False)  # llm, vector_db, web_search
    provider = Column(String(50), nullable=False)  # openai, pinecone, serper
    model = Column(String(100), nullable=True)  # gpt-4, claude-3, etc.
    config = Column(JSON, nullable=False)  # Rate limits, costs, capabilities
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserBudget(Base):
    """User budget and spending limits"""
    __tablename__ = "user_budgets"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    monthly_budget = Column(Float, nullable=False, default=100.0)
    current_usage = Column(Float, default=0.0)
    reset_date = Column(DateTime(timezone=True), nullable=False)
    max_per_request = Column(Float, nullable=False, default=10.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="budget")


class ApiKey(Base):
    """Encrypted API keys for external services"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service = Column(String(50), nullable=False)  # openai, pinecone, serper
    encrypted_key = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="api_keys") 