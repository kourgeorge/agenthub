"""Agent model for storing agent information."""

from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Text, Boolean, JSON, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    INACTIVE = "inactive"


class AgentType(str, Enum):
    """Agent type enumeration."""
    FUNCTION = "function"  # Traditional function-based agent
    ACP_SERVER = "acp_server"  # ACP server-based agent
    PERSISTENT = "persistent"  # Persistent agent with lifecycle management


class Agent(Base):
    """Agent model for storing agent information."""
    
    __tablename__ = "agents"
    
    # Override the base id field to use string-based abbreviated IDs
    id = Column(String(20), primary_key=True, index=True)
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    author = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    
    # Owner Information
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Agent Type and Configuration
    agent_type = Column(String(20), nullable=False, default=AgentType.FUNCTION.value)
    entry_point = Column(String(255), nullable=False)  # e.g., "main.py:AgentClass"
    requirements = Column(JSON, nullable=True)  # List of Python dependencies
    config_schema = Column(JSON, nullable=True)  # JSON schema for agent configuration
    
    # Agent Code and Assets
    code_zip_url = Column(String(500), nullable=True)  # URL to agent code ZIP
    code_hash = Column(String(64), nullable=True)  # SHA256 hash of code
    docker_image = Column(String(255), nullable=True)  # Docker image name
    code = Column(Text, nullable=True)  # Direct code storage (legacy - main file only)
    file_path = Column(String(500), nullable=True)  # Path to agent file
    
    # ACP Server Deployment (for ACP_SERVER type agents)
    acp_manifest = Column(JSON, nullable=True)  # ACP agent manifest
    deployment_config = Column(JSON, nullable=True)  # Docker deployment configuration
    server_port = Column(Integer, nullable=True)  # Port for ACP server
    health_check_endpoint = Column(String(255), nullable=True)  # Health check URL
    
    # Metadata
    tags = Column(JSON, nullable=True)  # List of tags
    category = Column(String(100), nullable=True)
    pricing_model = Column(String(50), nullable=True)  # "free", "per_use", "subscription"
    price_per_use = Column(Float, nullable=True)
    monthly_price = Column(Float, nullable=True)
    
    # Status and Validation
    status = Column(String(20), nullable=False, default=AgentStatus.DRAFT.value)
    is_public = Column(Boolean, default=False, nullable=False)
    validation_errors = Column(JSON, nullable=True)  # List of validation errors
    
    # Usage Statistics
    total_hires = Column(Integer, default=0, nullable=False)
    total_executions = Column(Integer, default=0, nullable=False)
    average_rating = Column(Float, default=0.0, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="owned_agents")
    hirings = relationship("Hiring", back_populates="agent")
    executions = relationship("Execution", back_populates="agent")
    files = relationship("AgentFile", back_populates="agent", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Agent(id='{self.id}', name='{self.name}', status='{self.status}', owner_id={self.owner_id})>"
    
    @classmethod
    def generate_id(cls, name: str, category: str = "general") -> str:
        """Generate a unique abbreviated ID for this agent."""
        return cls.generate_abbreviated_id(name, category)
    
    def get_main_file(self):
        """Get the main entry point file."""
        for file in self.files:
            if file.is_main_file == 'Y':
                return file
        return None
    
    def get_file_by_path(self, file_path: str):
        """Get a specific file by its path."""
        for file in self.files:
            if file.file_path == file_path:
                return file
        return None
    
    def get_all_files(self):
        """Get all files associated with this agent."""
        return [file for file in self.files] 