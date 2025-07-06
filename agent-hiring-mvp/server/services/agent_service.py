"""Agent service for managing agents."""

import hashlib
import logging
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.agent import Agent, AgentStatus
from ..models.user import User

logger = logging.getLogger(__name__)


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""
    name: str
    description: str
    version: str = "1.0.0"
    author: str
    email: str
    entry_point: str
    requirements: Optional[List[str]] = None
    config_schema: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    pricing_model: Optional[str] = None
    price_per_use: Optional[float] = None
    monthly_price: Optional[float] = None


class AgentService:
    """Service for managing agents."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_agent(self, agent_data: AgentCreateRequest, code_file_path: str) -> Agent:
        """Create a new agent."""
        # Calculate code hash
        code_hash = self._calculate_file_hash(code_file_path)
        
        # Extract and store agent code
        agent_code = self._extract_agent_code(code_file_path, agent_data.entry_point)
        
        # Create agent record
        agent = Agent(
            name=agent_data.name,
            description=agent_data.description,
            version=agent_data.version,
            author=agent_data.author,
            email=agent_data.email,
            entry_point=agent_data.entry_point,
            requirements=agent_data.requirements or [],
            config_schema=agent_data.config_schema,
            tags=agent_data.tags or [],
            category=agent_data.category,
            pricing_model=agent_data.pricing_model,
            price_per_use=agent_data.price_per_use,
            monthly_price=agent_data.monthly_price,
            code_hash=code_hash,
            code=agent_code,  # Store the extracted code
            status=AgentStatus.SUBMITTED.value,
            is_public=False,
        )
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Created agent: {agent.name} (ID: {agent.id})")
        return agent
    
    def get_agent(self, agent_id: int) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
    
    def get_public_agents(self, skip: int = 0, limit: int = 100) -> List[Agent]:
        """Get all public, approved agents."""
        return (
            self.db.query(Agent)
            .filter(Agent.is_public == True, Agent.status == AgentStatus.APPROVED.value)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def search_agents(self, query: str, category: Optional[str] = None) -> List[Agent]:
        """Search agents by name, description, or tags."""
        agents_query = self.db.query(Agent).filter(
            Agent.is_public == True,
            Agent.status == AgentStatus.APPROVED.value
        )
        
        if query:
            agents_query = agents_query.filter(
                Agent.name.ilike(f"%{query}%") |
                Agent.description.ilike(f"%{query}%")
            )
        
        if category:
            agents_query = agents_query.filter(Agent.category == category)
        
        return agents_query.all()
    
    def approve_agent(self, agent_id: int) -> Optional[Agent]:
        """Approve an agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        agent.status = AgentStatus.APPROVED.value
        agent.is_public = True
        agent.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Approved agent: {agent.name} (ID: {agent.id})")
        return agent
    
    def reject_agent(self, agent_id: int, reason: str) -> Optional[Agent]:
        """Reject an agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        agent.status = AgentStatus.REJECTED.value
        agent.validation_errors = [reason]
        agent.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Rejected agent: {agent.name} (ID: {agent.id}) - Reason: {reason}")
        return agent
    
    def update_agent_stats(self, agent_id: int, execution_count: int = 0, rating: Optional[float] = None) -> None:
        """Update agent statistics."""
        agent = self.get_agent(agent_id)
        if not agent:
            return
        
        if execution_count > 0:
            agent.total_executions += execution_count
        
        if rating is not None:
            # Simple average rating calculation
            current_total = agent.average_rating * (agent.total_executions - execution_count)
            new_total = current_total + (rating * execution_count)
            agent.average_rating = new_total / agent.total_executions
        
        self.db.commit()
    
    def _extract_agent_code(self, code_file_path: str, entry_point: str) -> str:
        """Extract agent code from ZIP file."""
        try:
            with zipfile.ZipFile(code_file_path, 'r') as zip_file:
                # Get the main agent file from entry_point
                # entry_point might be like "my_agent.py" or "my_agent.py:main"
                agent_file = entry_point.split(':')[0]
                
                # Try to find the agent file in the ZIP
                if agent_file in zip_file.namelist():
                    with zip_file.open(agent_file) as f:
                        return f.read().decode('utf-8')
                else:
                    # Fallback: find any Python file
                    python_files = [f for f in zip_file.namelist() if f.endswith('.py')]
                    if python_files:
                        with zip_file.open(python_files[0]) as f:
                            return f.read().decode('utf-8')
                    else:
                        raise Exception("No Python files found in ZIP")
        except Exception as e:
            logger.error(f"Error extracting agent code: {str(e)}")
            return ""
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def validate_agent_code(self, code_file_path: str) -> List[str]:
        """Validate agent code for security and compliance."""
        errors = []
        
        try:
            # Check if it's a valid ZIP file
            with zipfile.ZipFile(code_file_path, 'r') as zip_file:
                # Check for required files
                file_list = zip_file.namelist()
                
                if not any(f.endswith('.py') for f in file_list):
                    errors.append("No Python files found in the agent code")
                
                # Check for potentially dangerous files
                dangerous_extensions = ['.exe', '.bat', '.sh', '.ps1']
                for file_name in file_list:
                    if any(file_name.endswith(ext) for ext in dangerous_extensions):
                        errors.append(f"Potentially dangerous file found: {file_name}")
                
                # Check file size limits
                total_size = sum(zip_file.getinfo(f).file_size for f in file_list)
                if total_size > 10 * 1024 * 1024:  # 10MB limit
                    errors.append("Agent code exceeds size limit (10MB)")
        
        except zipfile.BadZipFile:
            errors.append("Invalid ZIP file")
        except Exception as e:
            errors.append(f"Error validating agent code: {str(e)}")
        
        return errors 