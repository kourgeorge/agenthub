"""Agent service for managing agents."""

import hashlib
import logging
import zipfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.agent import Agent, AgentStatus, AgentType
from ..models.agent_file import AgentFile
from ..models.user import User
from ..models.hiring import Hiring

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
    agent_type: Optional[str] = AgentType.FUNCTION.value
    acp_manifest: Optional[Dict[str, Any]] = None


class AgentService:
    """Service for managing agents."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_agent(self, agent_data: AgentCreateRequest, code_file_path: str, owner_id: int) -> Agent:
        """Create a new agent with multiple files."""
        # Calculate code hash
        code_hash = self._calculate_file_hash(code_file_path)
        
        # Extract all agent files
        agent_files = self._extract_all_agent_files(code_file_path, agent_data.entry_point)
        
        # Generate unique abbreviated ID
        agent_id = self._generate_unique_agent_id(agent_data.name, agent_data.category)
        
        # Create agent record
        agent = Agent(
            id=agent_id,  # Use the generated abbreviated ID
            name=agent_data.name,
            description=agent_data.description,
            version=agent_data.version,
            author=agent_data.author,
            email=agent_data.email,
            owner_id=owner_id,  # Set the owner ID
            entry_point=agent_data.entry_point,
            requirements=agent_data.requirements or [],
            config_schema=agent_data.config_schema,
            tags=agent_data.tags or [],
            category=agent_data.category,
            pricing_model=agent_data.pricing_model,
            price_per_use=agent_data.price_per_use,
            monthly_price=agent_data.monthly_price,
            agent_type=agent_data.agent_type or AgentType.FUNCTION.value,
            acp_manifest=agent_data.acp_manifest,
            code_hash=code_hash,
            # Keep legacy code field for backward compatibility (main file only)
            code=agent_files.get('main_file_content', ''),
            status=AgentStatus.SUBMITTED.value,
            is_public=False,
        )
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        # Create agent file records
        self._create_agent_file_records(agent.id, agent_files)
        
        logger.info(f"Created agent: {agent.name} (ID: {agent.id}) with {len(agent_files.get('files', []))} files for owner {owner_id}")
        return agent
    
    def _generate_unique_agent_id(self, name: str, category: str = "general") -> str:
        """Generate a unique abbreviated ID for the agent."""
        max_attempts = 10
        for attempt in range(max_attempts):
            agent_id = Agent.generate_id(name, category)
            
            # Check if this ID already exists
            existing_agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not existing_agent:
                return agent_id
            
            # If ID exists, try again with a different random suffix
            logger.warning(f"Agent ID {agent_id} already exists, retrying...")
        
        # If we still can't generate a unique ID after max attempts, add timestamp
        import time
        timestamp = int(time.time() % 10000)  # Last 4 digits of timestamp
        base_id = Agent.generate_id(name, category)
        return f"{base_id}{timestamp}"
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
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
    
    def get_my_agents(self, owner_id: int, skip: int = 0, limit: int = 100) -> List[Agent]:
        """Get all agents owned by a specific user, regardless of approval status."""
        return (
            self.db.query(Agent)
            .filter(Agent.owner_id == owner_id)
            .order_by(Agent.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def search_my_agents(self, owner_id: int, query: str, category: Optional[str] = None) -> List[Agent]:
        """Search agents owned by a specific user by name, description, or tags."""
        agents_query = self.db.query(Agent).filter(Agent.owner_id == owner_id)
        
        if query:
            agents_query = agents_query.filter(
                Agent.name.ilike(f"%{query}%") |
                Agent.description.ilike(f"%{query}%")
            )
        
        if category:
            agents_query = agents_query.filter(Agent.category == category)
        
        return agents_query.order_by(Agent.created_at.desc()).all()
    
    def get_agents_for_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Agent]:
        """Get all agents accessible to a user: public approved agents + their own agents."""
        # Get public, approved agents
        public_agents = self.get_public_agents(skip, limit)
        
        # Get user's own agents (regardless of approval status)
        own_agents = self.get_my_agents(user_id, 0, 1000)  # Get all own agents
        
        # Combine and deduplicate (in case user's agent is also public)
        all_agents = public_agents + own_agents
        seen_ids = set()
        unique_agents = []
        
        for agent in all_agents:
            if agent.id not in seen_ids:
                seen_ids.add(agent.id)
                unique_agents.append(agent)
        
        # Sort by creation date (newest first)
        unique_agents.sort(key=lambda x: x.created_at, reverse=True)
        
        # Apply pagination
        return unique_agents[skip:skip + limit]
    
    def search_agents_for_user(self, user_id: int, query: str, category: Optional[str] = None) -> List[Agent]:
        """Search agents accessible to a user: public approved agents + their own agents."""
        # Search public, approved agents
        public_agents = self.search_agents(query, category)
        
        # Search user's own agents
        own_agents = self.search_my_agents(user_id, query, category)
        
        # Combine and deduplicate
        all_agents = public_agents + own_agents
        seen_ids = set()
        unique_agents = []
        
        for agent in all_agents:
            if agent.id not in seen_ids:
                seen_ids.add(agent.id)
                unique_agents.append(agent)
        
        # Sort by creation date (newest first)
        unique_agents.sort(key=lambda x: x.created_at, reverse=True)
        
        return unique_agents
    
    def approve_agent(self, agent_id: str) -> Optional[Agent]:
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
    
    def reject_agent(self, agent_id: str, reason: str) -> Optional[Agent]:
        """Reject an agent and handle existing hirings and deployments."""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        # Update agent status
        agent.status = AgentStatus.REJECTED.value
        agent.validation_errors = [reason]
        agent.updated_at = datetime.utcnow()
        
        # Handle ALL existing hirings for this agent (not just active ones)
        all_hirings = self.db.query(Hiring).filter(
            Hiring.agent_id == agent_id
        ).all()
        
        active_hirings_count = 0
        for hiring in all_hirings:
            # For active hirings, suspend them
            if hiring.status == "active":
                hiring.status = "suspended"
                hiring.updated_at = datetime.utcnow()
                active_hirings_count += 1
        
        # Clean up ALL deployments for this agent (comprehensive approach)
        self._cleanup_all_agent_deployments(agent_id)
        
        # Block new executions for this agent
        # (This is handled by the hiring service which checks agent status)
        
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Rejected agent: {agent.name} (ID: {agent.id}) - Reason: {reason}")
        logger.info(f"Processed {len(all_hirings)} total hirings, suspended {active_hirings_count} active hirings for rejected agent")
        
        return agent
    
    def _stop_hiring_deployment(self, hiring: Hiring):
        """Stop deployment for a hiring (for ACP agents)."""
        try:
            from .deployment_service import DeploymentService
            from ..models.deployment import AgentDeployment
            
            deployment_service = DeploymentService(self.db)
            
            # Find existing deployment
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                logger.info(f"Stopping deployment {deployment.deployment_id} for rejected agent")
                stop_result = deployment_service.stop_deployment(deployment.deployment_id, timeout=60)
                if "error" in stop_result:
                    logger.error(f"Failed to stop deployment {deployment.deployment_id}: {stop_result['error']}")
                else:
                    logger.info(f"Successfully stopped deployment {deployment.deployment_id}")
                    
                    # Note: Deployment status is managed by HiringService, not here
                    # This method only handles container stopping, not deployment lifecycle
                    logger.info(f"Stopped deployment {deployment.deployment_id} for hiring {hiring.id}")
        except Exception as e:
            logger.error(f"Exception stopping hiring deployment: {e}")
    
    def _stop_function_deployment(self, hiring: Hiring):
        """Stop deployment for a hiring (for function agents)."""
        try:
            from .function_deployment_service import FunctionDeploymentService
            from ..models.deployment import AgentDeployment
            
            deployment_service = FunctionDeploymentService(self.db)
            
            # Find existing deployment
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                logger.info(f"Stopping function deployment {deployment.deployment_id} for rejected agent")
                stop_result = deployment_service.stop_function_deployment(deployment.deployment_id)
                if "error" in stop_result:
                    logger.error(f"Failed to stop function deployment {deployment.deployment_id}: {stop_result['error']}")
                else:
                    logger.info(f"Successfully stopped function deployment {deployment.deployment_id}")
                    
                    # Note: Deployment status is managed by HiringService, not here
                    # This method only handles container stopping, not deployment lifecycle
                    logger.info(f"Stopped function deployment {deployment.deployment_id} for hiring {hiring.id}")
        except Exception as e:
            logger.error(f"Exception stopping function deployment: {e}")
    
    def _cleanup_all_agent_deployments(self, agent_id: str):
        """Clean up all deployments for an agent (direct approach)."""
        try:
            from ..models.deployment import AgentDeployment
            from .deployment_service import DeploymentService
            from .function_deployment_service import FunctionDeploymentService
            
            # Find all deployments for this agent
            deployments = self.db.query(AgentDeployment).filter(
                AgentDeployment.agent_id == agent_id
            ).all()
            
            if not deployments:
                logger.info(f"No deployments found for agent {agent_id}")
                return
            
            logger.info(f"Found {len(deployments)} deployments to clean up for agent {agent_id}")
            
            deployment_service = DeploymentService(self.db)
            function_deployment_service = FunctionDeploymentService(self.db)
            
            for deployment in deployments:
                try:
                    logger.info(f"Cleaning up deployment {deployment.deployment_id} for agent {agent_id}")
                    
                    # Stop the deployment based on agent type
                    if deployment.agent.agent_type == "acp_server":
                        stop_result = deployment_service.stop_deployment(deployment.deployment_id, timeout=60)
                    elif deployment.agent.agent_type == "persistent":
                        # For persistent agents, try to cleanup first, then stop
                        try:
                            cleanup_result = deployment_service.cleanup_persistent_agent(deployment.deployment_id)
                            if "error" in cleanup_result:
                                logger.warning(f"Failed to cleanup persistent agent {deployment.deployment_id}: {cleanup_result['error']}")
                            else:
                                logger.info(f"Successfully cleaned up persistent agent {deployment.deployment_id}")
                        except Exception as e:
                            logger.warning(f"Error during persistent agent cleanup: {e}")
                        stop_result = deployment_service.stop_deployment(deployment.deployment_id, timeout=60)
                    else:
                        stop_result = function_deployment_service.stop_function_deployment(deployment.deployment_id)
                    
                    if "error" in stop_result:
                        logger.error(f"Failed to stop deployment {deployment.deployment_id}: {stop_result['error']}")
                    else:
                        logger.info(f"Successfully stopped deployment {deployment.deployment_id}")
                    
                    # Note: Deployment status is managed by HiringService, not here
                    # This method only handles container stopping, not deployment lifecycle
                    logger.info(f"Stopped deployment {deployment.deployment_id}")
                    
                except Exception as e:
                    logger.error(f"Exception cleaning up deployment {deployment.deployment_id}: {e}")
            
            self.db.commit()
            logger.info(f"Completed cleanup of {len(deployments)} deployments for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Exception in _cleanup_all_agent_deployments: {e}")
    
    def update_agent_stats(self, agent_id: str, execution_count: int = 0, rating: Optional[float] = None) -> None:
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
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _extract_all_agent_files(self, code_file_path: str, entry_point: str) -> Dict[str, Any]:
        """Extract all files from ZIP file."""
        files_data = {
            'files': [],
            'main_file_content': '',
            'main_file_path': ''
        }
        
        try:
            with zipfile.ZipFile(code_file_path, 'r') as zip_file:
                # Get the main agent file from entry_point
                # entry_point might be like "my_agent.py" or "my_agent.py:main"
                main_file = entry_point.split(':')[0]
                
                # Extract all files
                for file_name in zip_file.namelist():
                    # Skip directories
                    if file_name.endswith('/'):
                        continue
                    
                    try:
                        with zip_file.open(file_name) as f:
                            content = f.read().decode('utf-8')
                            
                            # Determine file type
                            file_ext = Path(file_name).suffix.lower()
                            is_executable = file_ext in ['.py', '.js', '.sh', '.bat']
                            is_main_file = file_name == main_file
                            
                            file_data = {
                                'file_path': file_name,
                                'file_name': Path(file_name).name,
                                'file_content': content,
                                'file_type': file_ext,
                                'file_size': len(content.encode('utf-8')),
                                'is_main_file': 'Y' if is_main_file else 'N',
                                'is_executable': 'Y' if is_executable else 'N'
                            }
                            
                            files_data['files'].append(file_data)
                            
                            # Store main file content for backward compatibility
                            if is_main_file:
                                files_data['main_file_content'] = content
                                files_data['main_file_path'] = file_name
                                
                    except UnicodeDecodeError:
                        # Skip binary files
                        logger.warning(f"Skipping binary file: {file_name}")
                        continue
                
                # If no main file found, use first Python file as fallback
                if not files_data['main_file_content']:
                    python_files = [f for f in files_data['files'] if f['file_type'] == '.py']
                    if python_files:
                        files_data['main_file_content'] = python_files[0]['file_content']
                        files_data['main_file_path'] = python_files[0]['file_path']
                        python_files[0]['is_main_file'] = 'Y'
                
        except Exception as e:
            logger.error(f"Error extracting agent files: {str(e)}")
            raise Exception(f"Failed to extract agent files: {str(e)}")
        
        return files_data
    
    def _create_agent_file_records(self, agent_id: str, files_data: Dict[str, Any]) -> None:
        """Create database records for all agent files."""
        for file_data in files_data.get('files', []):
            agent_file = AgentFile(
                agent_id=agent_id,
                file_path=file_data['file_path'],
                file_name=file_data['file_name'],
                file_content=file_data['file_content'],
                file_type=file_data['file_type'],
                file_size=file_data['file_size'],
                is_main_file=file_data['is_main_file'],
                is_executable=file_data['is_executable']
            )
            self.db.add(agent_file)
        
        self.db.commit()
    
    def get_agent_files(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all files for an agent."""
        agent_files = self.db.query(AgentFile).filter(AgentFile.agent_id == agent_id).all()
        return [file.to_dict() for file in agent_files]
    
    def get_agent_file_content(self, agent_id: str, file_path: str) -> Optional[str]:
        """Get content of a specific file for an agent."""
        agent_file = self.db.query(AgentFile).filter(
            AgentFile.agent_id == agent_id,
            AgentFile.file_path == file_path
        ).first()
        return agent_file.file_content if agent_file else None
    
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
                
                # Check individual file size limits
                for file_name in file_list:
                    file_size = zip_file.getinfo(file_name).file_size
                    if file_size > 1 * 1024 * 1024:  # 1MB per file limit
                        errors.append(f"File {file_name} exceeds size limit (1MB)")
        
        except zipfile.BadZipFile:
            errors.append("Invalid ZIP file")
        except Exception as e:
            errors.append(f"Error validating agent code: {str(e)}")
        
        return errors 