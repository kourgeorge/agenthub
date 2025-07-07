"""Deployment model for tracking ACP agent deployments."""

from enum import Enum
from typing import Optional
from datetime import datetime

from sqlalchemy import Column, String, Integer, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    CRASHED = "crashed"


class AgentDeployment(Base):
    """Model for tracking ACP agent deployments."""
    
    __tablename__ = "agent_deployments"
    
    # Deployment Information
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    hiring_id = Column(Integer, ForeignKey("hirings.id"), nullable=False)
    deployment_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # Container Information
    container_id = Column(String(255), nullable=True)  # Docker container ID
    container_name = Column(String(255), nullable=True)  # Docker container name
    docker_image = Column(String(255), nullable=True)  # Docker image used
    
    # Network Configuration
    internal_port = Column(Integer, nullable=False, default=8001)  # Container internal port
    external_port = Column(Integer, nullable=True)  # Host external port
    proxy_endpoint = Column(String(255), nullable=True)  # Proxy endpoint URL
    
    # Deployment Status
    status = Column(String(20), nullable=False, default=DeploymentStatus.PENDING.value)
    status_message = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    
    # Resource Usage
    cpu_usage = Column(JSON, nullable=True)  # CPU usage metrics
    memory_usage = Column(JSON, nullable=True)  # Memory usage metrics
    
    # Configuration
    environment_vars = Column(JSON, nullable=True)  # Environment variables
    deployment_config = Column(JSON, nullable=True)  # Full deployment configuration
    
    # Health Status
    is_healthy = Column(Boolean, default=False, nullable=False)
    health_check_failures = Column(Integer, default=0, nullable=False)
    
    # Relationships
    agent = relationship("Agent", backref="deployments")
    hiring = relationship("Hiring", backref="deployment")
    
    def __repr__(self) -> str:
        return f"<AgentDeployment(id={self.id}, deployment_id='{self.deployment_id}', status='{self.status}')>" 