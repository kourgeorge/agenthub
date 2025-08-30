"""Deployment service for managing ACP agent Docker containers."""

import os
import json
import shutil
import logging
import docker
from docker import errors as docker_errors
import uuid
import asyncio
import aiohttp
import requests
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import socket

from sqlalchemy.orm import Session
from ..models.agent import Agent, AgentType
from ..models.hiring import Hiring
from ..models.deployment import AgentDeployment, DeploymentStatus
from .env_service import EnvironmentService
from .container_utils import generate_container_name, generate_docker_image_name
from .resource_limits import get_agent_resource_limits, to_docker_config

logger = logging.getLogger(__name__)


class DeploymentService:
    """Service for managing ACP agent deployments."""
    
    def __init__(self, db: Session):
        self.db = db
        self.docker_client = docker.from_env()
        self.base_port = 8001
        self.max_port = 9000
        
        # Use cross-platform temporary directory
        # Try environment variable first, then system temp
        temp_base = os.getenv("AGENTHUB_TEMP_DIR") or tempfile.gettempdir()
        self.deployment_dir = Path(temp_base) / "agent_deployments"
        self.deployment_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure server hostname for proxy endpoints
        self.server_hostname = self._get_server_hostname()
        
        # Initialize environment service for external API keys
        self.env_service = EnvironmentService()
    
    def _get_agent_env_path(self, agent: Agent) -> Optional[str]:
        """
        Get the path to the agent's .env file if it exists.
        
        Args:
            agent: The agent object
            
        Returns:
            Path to agent's .env file or None if not found
        """
        # Check if agent has a .env file in its files
        if agent.files:
            for agent_file in agent.files:
                if agent_file.file_path == '.env':
                    # Create a temporary .env file for the agent
                    import tempfile
                    temp_dir = Path(tempfile.gettempdir())
                    agent_env_path = temp_dir / f"agent_{agent.id}_env_{uuid.uuid4().hex[:8]}.env"
                    
                    with open(agent_env_path, 'w') as f:
                        f.write(agent_file.file_content)
                    
                    logger.info(f"Created temporary agent .env file: {agent_env_path}")
                    return str(agent_env_path)
        
        return None
        
    def _get_server_hostname(self) -> str:
        """Get the server hostname for proxy endpoints."""
        # 1. Check environment variable first (allows manual override)
        hostname = os.getenv("AGENTHUB_HOSTNAME")
        if hostname:
            return hostname
        
        # 2. Try to get external IP from request context (if available)
        # This would need to be passed from FastAPI context
        
        # 3. Get local machine's IP address (fallback)
        try:
            # Connect to a remote server to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            # Final fallback - get hostname
            try:
                return socket.getfqdn()
            except Exception:
                # Ultimate fallback
                return "localhost"
    
    def get_available_port(self) -> int:
        """Get an available port for deployment."""
        used_ports = {
            deployment.external_port 
            for deployment in self.db.query(AgentDeployment).all()
            if deployment.external_port
        }
        
        for port in range(self.base_port, self.max_port):
            if port not in used_ports:
                return port
        
        raise RuntimeError("No available ports for deployment")
    
    def create_deployment(self, hiring_id: int) -> Dict[str, Any]:
        """Create a new deployment for a hired agent (any type)."""
        try:
            # Get hiring and agent information
            hiring = self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
            if not hiring:
                return {"error": "Hiring not found"}
            
            agent = hiring.agent
            if not agent:
                return {"error": "Agent not found"}
            
            # Accept all agent types (function, persistent, acp)
            if agent.agent_type not in ["function", "persistent", "acp"]:
                return {"error": f"Unsupported agent type: {agent.agent_type}"}
            
            # Check if deployment already exists
            existing_deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring_id
            ).first()
            
            if existing_deployment:
                return {"error": "Deployment already exists", "deployment_id": existing_deployment.deployment_id}
            
            # Generate deployment ID with agent type - use Docker-compliant format
            user_id = hiring.user_id or "anon"
            agent_type = agent.agent_type
            # Use underscores and lowercase for better Docker compatibility
            safe_agent_id = str(agent.id).lower().replace('-', '_')
            deployment_id = f"{agent_type}_{safe_agent_id}_{hiring_id}_{uuid.uuid4().hex[:8]}"
            
            # Create deployment record
            deployment_config = {
                "agent_id": agent.id,
                "hiring_id": hiring_id,
                "deployment_id": deployment_id,
                "status": DeploymentStatus.PENDING.value,
                "deployment_type": agent.agent_type,
                "environment_vars": {
                    "DEPLOYMENT_ID": deployment_id,
                    "AGENT_ID": str(agent.id),
                    "HIRING_ID": str(hiring_id),
                    "USER_ID": str(user_id),
                    "AGENT_TYPE": agent.agent_type
                }
            }
            
            # Add port configuration only for server-based agents (acp)
            if agent.agent_type == "acp":
                external_port = self.get_available_port()
                deployment_config["external_port"] = external_port
                deployment_config["proxy_endpoint"] = f"http://{self.server_hostname}:{external_port}"
                deployment_config["environment_vars"]["PORT"] = "8001"
            
            deployment = AgentDeployment(**deployment_config)
            
            self.db.add(deployment)
            self.db.commit()
            
            logger.info(f"Created deployment {deployment_id} for agent {agent.id}")
            
            result = {
                "deployment_id": deployment_id,
                "status": "created"
            }
            
            # Add port info only for server-based agents
            if agent.agent_type == "acp":
                result["external_port"] = deployment.external_port
                result["proxy_endpoint"] = deployment.proxy_endpoint
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create deployment: {e}")
            return {"error": str(e)}
    
    async def build_and_deploy(self, deployment_id: str) -> Dict[str, Any]:
        """Build Docker image and deploy the agent asynchronously."""
        try:
            # Get deployment
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            # Update status to building
            deployment.status = DeploymentStatus.BUILDING.value
            self.db.commit()
            
            # Get agent
            agent = deployment.agent
            
            # Create deployment directory
            deploy_dir = self.deployment_dir / deployment_id
            deploy_dir.mkdir(exist_ok=True)
            
            # Extract agent code
            self._extract_agent_code(agent, deploy_dir)
            
            # Initialize image_name variable
            image_name = None
            
            # Check if agent already has a pre-built image
            logger.info(f"🔍 Checking for pre-built Docker image for agent {agent.id}")
            logger.info(f"Agent docker_image field: {agent.docker_image}")
            
            if agent.docker_image:
                expected_prefix = f"agenthub_{agent.agent_type.lower().replace('-', '_')}_prebuild"
                logger.info(f"Expected pre-built image prefix: {expected_prefix}")
                
                if agent.docker_image.startswith(expected_prefix):
                    logger.info(f"✅ Found pre-built Docker image {agent.docker_image} for agent {agent.id}")
                    image_name = agent.docker_image
                    # Verify the image exists in Docker
                    try:
                        self.docker_client.images.get(image_name)
                        logger.info(f"🐳 Pre-built image {image_name} verified in Docker - USING PRE-BUILT IMAGE")
                    except docker_errors.ImageNotFound:
                        logger.warning(f"⚠️ Pre-built image {image_name} not found in Docker, will build new image")
                        image_name = None
                else:
                    logger.info(f"Agent has docker_image but doesn't match pre-built pattern: {agent.docker_image}")
            else:
                logger.info(f"No docker_image field found for agent {agent.id}")
            
            # Build new image if no pre-built image available
            if not image_name:
                logger.info(f"🔨 Building new Docker image from scratch for agent {agent.id}")
                # Build Docker image using centralized utility
                user_id = deployment.hiring.user_id or "anon"
                agent_type = agent.agent_type
                hiring_id = deployment.hiring_id
                deployment_uuid = deployment_id.split('_')[-1]  # Get the UUID part
                image_name = generate_docker_image_name(agent_type, user_id, agent.id, hiring_id, deployment_uuid)
                
                logger.info(f"Building new Docker image: {image_name}")
                # Build Docker image asynchronously
                image = await self._build_docker_image(deploy_dir, image_name)
            else:
                logger.info(f"🚀 FAST DEPLOYMENT: Using pre-built image {image_name} - skipping Docker build")
            
            # Ensure image_name is set before proceeding
            if not image_name:
                raise Exception("Failed to determine Docker image name for deployment")
            
            # Update deployment with image info
            deployment.docker_image = image_name
            deployment.status = DeploymentStatus.DEPLOYING.value
            self.db.commit()
            
            # Deploy container asynchronously
            container = await self._deploy_container(deployment, image_name)
            
            # Update deployment with container info
            deployment.container_id = container.id
            deployment.container_name = container.name
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.started_at = datetime.now(timezone.utc)
            self.db.commit()
            
            logger.info(f"Successfully deployed agent {agent.id} as {deployment_id}")
            
            return {
                "deployment_id": deployment_id,
                "status": "deployed",
                "container_id": container.id,
                "proxy_endpoint": deployment.proxy_endpoint
            }
            
        except Exception as e:
            logger.error(f"Failed to deploy {deployment_id}: {e}")
            
            # Update deployment status
            if deployment:
                deployment.status = DeploymentStatus.FAILED.value
                deployment.status_message = str(e)
                self.db.commit()
            
            return {"error": str(e)}
    
    def _extract_agent_code(self, agent: Agent, deploy_dir: Path):
        """Extract agent code to deployment directory."""
        if agent.code_zip_url:
            # Download and extract ZIP
            # TODO: Implement ZIP download and extraction
            pass
        elif agent.files:
            # Use new multi-file approach
            self._extract_agent_files(agent, deploy_dir)
        elif agent.code:
            # Legacy single-file approach
            main_file = deploy_dir / "main.py"
            main_file.write_text(agent.code, encoding='utf-8')
        else:
            raise ValueError("No agent code available")
        
        # Create basic requirements.txt if not exists
        requirements_file = deploy_dir / "requirements.txt"
        if not requirements_file.exists():
            requirements = agent.requirements or []
            requirements_file.write_text("\n".join(requirements), encoding='utf-8')
        
        # Create merged .env file with external API keys
        agent_env_path = self._get_agent_env_path(agent)
        merged_env_path = self.env_service.create_merged_env_file(
            agent_env_path=agent_env_path,
            output_path=str(deploy_dir / ".env")
        )
        logger.info(f"Created merged .env file for deployment: {merged_env_path}")
        
        # Create Dockerfile based on agent type
        dockerfile = deploy_dir / "Dockerfile"
        if not dockerfile.exists():
            agent_type = agent.agent_type
            
            if agent_type == "function":
                # Function agents run once and exit
                dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Function agents run once and exit
CMD ["python", "main.py"]
"""
            elif agent_type == "persistent":
                # Persistent agents stay running and use docker exec for operations
                dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create state directory for persistent agents
RUN mkdir -p /app/state

# Set environment variables
ENV PYTHONPATH=/app
ENV STATE_DIR=/app/state
ENV PYTHONUNBUFFERED=1

# Keep container running for persistent agent execution
CMD ["tail", "-f", "/dev/null"]
"""
            else:  # acp or other types
                # ACP agents run a server
                dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["python", "main.py"]
"""
            
            dockerfile.write_text(dockerfile_content, encoding='utf-8')
    
    def _extract_agent_files(self, agent: Agent, deploy_dir: Path):
        """Extract all agent files to deployment directory."""
        # Ensure agent.files is properly loaded and not a coroutine
        if hasattr(agent.files, '__await__'):
            logger.error("agent.files is a coroutine - this indicates a database session issue")
            raise RuntimeError("agent.files is a coroutine - database session issue")
        
        if not agent.files:
            logger.warning(f"No files found for agent {agent.id}")
            return
            
        for agent_file in agent.files:
            # Create directory structure if needed
            file_path = deploy_dir / agent_file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            file_path.write_text(agent_file.file_content, encoding='utf-8')
            
            logger.info(f"Extracted file: {agent_file.file_path}")
        
        # For persistent agents, include the agenthub_sdk files
        if agent.agent_type == "persistent":
            self._include_sdk_files(deploy_dir)
        
        # Ensure main.py exists (for backward compatibility)
        main_file = deploy_dir / "main.py"
        if not main_file.exists():
            # Find the main file
            main_agent_file = agent.get_main_file()
            if main_agent_file:
                main_file.write_text(main_agent_file.file_content, encoding='utf-8')
            else:
                # Fallback to first Python file
                python_files = [f for f in agent.files if f.file_type == '.py']
                if python_files:
                    main_file.write_text(python_files[0].file_content, encoding='utf-8')
    
    def _include_sdk_files(self, deploy_dir: Path):
        """Include agenthub_sdk files for persistent agents."""
        try:
            # Create agenthub_sdk directory
            sdk_dir = deploy_dir / "agenthub_sdk"
            sdk_dir.mkdir(exist_ok=True)
            
            # Create __init__.py
            init_file = sdk_dir / "__init__.py"
            init_file.write_text("""#!/usr/bin/env python3
\"\"\"
AgentHub SDK - Agent Base Classes and Utilities
\"\"\"

from .agent import Agent, PersistentAgent

__all__ = ['Agent', 'PersistentAgent']
""", encoding='utf-8')
            
            # Create agent.py with the base classes
            agent_file = sdk_dir / "agent.py"
            agent_file.write_text("""#!/usr/bin/env python3
\"\"\"
AgentHub SDK - Agent Base Classes and Utilities
\"\"\"

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Agent(ABC):
    \"\"\"Base class for all agents.\"\"\"
    
    def __init__(self):
        \"\"\"Initialize the agent.\"\"\"
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Execute the agent with input data and configuration.
        
        Args:
            input_data: Input data for execution
            config: Configuration data for the agent
            
        Returns:
            Dict with execution result
        \"\"\"
        pass


class PersistentAgent(ABC):
    \"\"\"
    Base class for persistent agents with state management.
    
    This class provides:
    - State management (_get_state/_set_state)
    - Lifecycle management (_is_initialized/_mark_initialized)
    - Abstract methods for agent implementation
    
    The platform handles all platform concerns (IDs, tracking, etc.).
    Agents focus only on business logic.
    \"\"\"
    
    def __init__(self):
        self._state = {}
        self._initialized = False
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Initialize the agent with configuration.\"\"\"
        pass
    
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Execute the agent with input_data.\"\"\"
        pass
    
    def cleanup(self) -> Dict[str, Any]:
        \"\"\"Clean up agent resources.\"\"\"
        return {\"status\": \"cleaned_up\", \"message\": \"Default cleanup completed\"}
    
    def _get_state(self, key: str, default: Any = None) -> Any:
        \"\"\"Get value from agent state.\"\"\"
        return self._state.get(key, default)
    
    def _set_state(self, key: str, value: Any) -> None:
        \"\"\"Set value in agent state.\"\"\"
        self._state[key] = value
    
    def _is_initialized(self) -> bool:
        \"\"\"Check if agent is initialized.\"\"\"
        return self._initialized
    
    def _mark_initialized(self) -> None:
        \"\"\"Mark agent as initialized.\"\"\"
        self._initialized = True
""", encoding='utf-8')
            
            logger.info("Included agenthub_sdk files for persistent agent")
            
        except Exception as e:
            logger.error(f"Failed to include SDK files: {e}")
            # Don't fail the deployment if SDK inclusion fails
    
    async def _build_docker_image(self, deploy_dir: Path, image_name: str):
        """Build Docker image for the agent asynchronously."""
        logger.info(f"Building Docker image {image_name}")
        
        # Run Docker build in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Add timeout to prevent hanging builds
        try:
            image, logs = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.docker_client.images.build(
                        path=str(deploy_dir),
                        tag=image_name,
                        rm=True,
                        forcerm=True
                    )
                ),
                timeout=300  # 5 minutes timeout
            )
            
            # Log build output
            for log in logs:
                if isinstance(log, dict) and 'stream' in log:
                    stream_content = log['stream']
                    if isinstance(stream_content, str):
                        logger.info(f"Build: {stream_content.strip()}")
            
            return image
            
        except asyncio.TimeoutError:
            logger.error(f"Docker build timed out for {image_name} after 5 minutes")
            raise Exception(f"Docker build timed out for {image_name}")
        except Exception as e:
            logger.error(f"Docker build failed for {image_name}: {e}")
            raise

    def pre_build_agent_image(self, agent: Agent) -> Optional[str]:
        """Pre-build Docker image for an agent without creating a deployment."""
        try:
            logger.info(f"Pre-building Docker image for agent {agent.id}")
            
            # Verify Docker daemon is accessible
            try:
                self.docker_client.ping()
            except Exception as e:
                logger.error(f"Docker daemon is not accessible: {e}")
                return None
            
            # Create temporary deployment directory
            temp_deploy_dir = self.deployment_dir / f"prebuild_{agent.id}_{uuid.uuid4().hex[:8]}"
            temp_deploy_dir.mkdir(exist_ok=True)
            
            try:
                # Extract agent code
                self._extract_agent_code(agent, temp_deploy_dir)
                
                # Verify files were created
                requirements_file = temp_deploy_dir / "requirements.txt"
                dockerfile = temp_deploy_dir / "Dockerfile"
                
                # Ensure requirements.txt exists and is not empty
                if requirements_file.exists():
                    with open(requirements_file, 'r') as f:
                        requirements_content = f.read()
                        if not requirements_content.strip():
                            logger.warning("Requirements.txt is empty, adding basic requirements")
                            with open(requirements_file, 'w') as f:
                                f.write("requests>=2.25.0\n")
                else:
                    logger.warning("Requirements.txt not found, creating basic one")
                    with open(requirements_file, 'w') as f:
                        f.write("requests>=2.25.0\n")
                
                if not dockerfile.exists():
                    logger.error("Dockerfile not found, cannot proceed with build")
                    return None
                
                # Generate image name for pre-built image
                # Use a valid Docker image naming convention
                prebuild_uuid = uuid.uuid4().hex[:8]
                # Docker image names must follow: [a-z0-9][a-z0-9._-]*
                # Replace hyphens with underscores and ensure valid format
                # IMPORTANT: Docker image names must be entirely lowercase
                safe_agent_type = agent.agent_type.lower().replace('-', '_')
                safe_agent_id = agent.id.lower().replace('-', '_')
                image_name = f"agenthub_{safe_agent_type}_prebuild_{safe_agent_id}_{prebuild_uuid}"
                
                # Build Docker image with timeout
                try:
                    logger.info(f"Building Docker image {image_name}")
                    
                    # Use a cross-platform timeout approach
                    import threading
                    import time
                    
                    build_result = {"image": None, "logs": None, "error": None, "completed": False}
                    
                    def docker_build():
                        try:
                            image, logs = self.docker_client.images.build(
                                path=str(temp_deploy_dir),
                                tag=image_name,
                                rm=True,
                                forcerm=True
                            )
                            build_result["image"] = image
                            build_result["logs"] = logs
                            build_result["completed"] = True
                        except Exception as e:
                            build_result["error"] = e
                            logger.error(f"Docker build failed in thread: {e}")
                    
                    # Start build in a separate thread
                    build_thread = threading.Thread(target=docker_build)
                    build_thread.daemon = True
                    build_thread.start()
                    
                    # Wait for build to complete or timeout
                    timeout_seconds = 300  # 5 minutes
                    start_time = time.time()
                    
                    while not build_result["completed"] and build_result["error"] is None:
                        if time.time() - start_time > timeout_seconds:
                            logger.error(f"Docker build timed out for {image_name} after {timeout_seconds} seconds")
                            return None
                        time.sleep(1)  # Check every second
                    
                    # Check for errors
                    if build_result["error"]:
                        logger.error(f"Docker build failed for {image_name}: {build_result['error']}")
                        return None
                    
                    logger.info(f"Successfully pre-built Docker image {image_name} for agent {agent.id}")
                    logger.info(f"📦 Image will be stored in agent.docker_image field for future use")
                    return image_name
                    
                except Exception as e:
                    logger.error(f"Docker build failed for {image_name}: {e}")
                    return None
                        
            finally:
                # Clean up temporary directory
                try:
                    shutil.rmtree(temp_deploy_dir)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary directory {temp_deploy_dir}: {e}")
                    
        except Exception as e:
            logger.error(f"Error pre-building Docker image for agent {agent.id}: {e}")
            return None

    def remove_prebuilt_image(self, image_name: str) -> bool:
        """Remove a pre-built Docker image."""
        try:
            logger.info(f"Removing pre-built Docker image: {image_name}")
            
            # Check if image exists
            try:
                image = self.docker_client.images.get(image_name)
                logger.info(f"Found image {image_name}, removing it")
                
                # Remove the image
                self.docker_client.images.remove(image_name, force=True)
                logger.info(f"Successfully removed pre-built image {image_name}")
                return True
                
            except docker_errors.ImageNotFound:
                logger.info(f"Image {image_name} not found, nothing to remove")
                return True
                
        except Exception as e:
            logger.error(f"Failed to remove pre-built image {image_name}: {e}")
            return False


    async def _deploy_container(self, deployment: AgentDeployment, image_name: str):
        """Deploy Docker container for the agent asynchronously."""
        user_id = deployment.hiring.user_id or "anon"
        agent_type = deployment.deployment_type or "function"
        
        # Use centralized container naming
        container_name = generate_container_name(deployment)
        
        logger.info(f"Deploying container {container_name}")
        
        # Container configuration
        container_config = {
            "image": image_name,
            "name": container_name,
            "environment": deployment.environment_vars,
            "detach": True,
            "labels": {
                "monitoring": "true",
                "agent_type": agent_type,
                "deployment_id": deployment.deployment_id,
                "agent_id": str(deployment.agent_id),
                "hiring_id": str(deployment.hiring_id),
                "user_id": str(user_id),
                "service": "agenthub-agent"
            }
        }
        
        # Add resource limits
        try:
            # Get resource limits for the agent
            resource_limits = get_agent_resource_limits(deployment.agent_id)
            docker_config = to_docker_config(resource_limits)
            container_config.update(docker_config)
            
            # Run container creation in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Add timeout to prevent hanging container creation
            try:
                container = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: self.docker_client.containers.run(**container_config)
                    ),
                    timeout=600  # 10 minutes timeout for long-running agent deployments
                )
            except asyncio.TimeoutError:
                logger.error(f"Container creation timed out for {container_name} after 10 minutes")
                raise Exception(f"Container creation timed out for {container_name}")
            except Exception as e:
                logger.error(f"Container creation failed for {container_name}: {e}")
                raise
            
            # Update deployment with container info
            deployment.container_id = container.id
            deployment.container_name = container_name
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.deployed_at = datetime.now(timezone.utc)
            deployment.is_healthy = True
            deployment.health_check_failures = 0
            deployment.last_health_check = datetime.now(timezone.utc)
            
            # Get container port mapping
            container.reload()
            if container.ports:
                # Extract the first exposed port
                for container_port, host_ports in container.ports.items():
                    if host_ports:
                        deployment.external_port = int(host_ports[0]['HostPort'])
                        break
            
            self.db.commit()
            
            logger.info(f"Container {container_name} deployed successfully with ID {container.id}")
            return container
            
        except Exception as e:
            logger.error(f"Failed to deploy container {container_name}: {e}")
            deployment.status = DeploymentStatus.FAILED.value
            deployment.error_message = str(e)
            self.db.commit()
            raise
    
    def suspend_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Suspend a deployment by stopping the container but keeping it."""
        try:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            # Stop container but don't remove it
            if deployment.container_id:
                try:
                    container = self.docker_client.containers.get(deployment.container_id)
                    logger.info(f"Suspending container {deployment.container_id}...")
                    
                    # Stop the container but don't remove it
                    container.stop(timeout=30)
                    logger.info(f"Container {deployment.container_id} suspended (stopped but not removed)")
                        
                except docker_errors.NotFound:
                    logger.warning(f"Container {deployment.container_id} not found")
                except Exception as e:
                    logger.error(f"Error suspending container {deployment.container_id}: {e}")
                    return {"error": f"Failed to suspend container: {str(e)}"}
            
            # Update deployment status
            deployment.status = DeploymentStatus.STOPPED.value
            deployment.stopped_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return {"deployment_id": deployment_id, "status": "suspended"}
            
        except Exception as e:
            logger.error(f"Failed to suspend deployment {deployment_id}: {e}")
            return {"error": str(e)}

    def resume_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Resume a suspended deployment by starting the stopped container."""
        try:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            # Start the stopped container
            if deployment.container_id:
                try:
                    container = self.docker_client.containers.get(deployment.container_id)
                    logger.info(f"Resuming container {deployment.container_id}...")
                    
                    # Start the container
                    container.start()
                    logger.info(f"Container {deployment.container_id} resumed")
                        
                except docker_errors.NotFound:
                    logger.warning(f"Container {deployment.container_id} not found - may need to redeploy")
                    # If container not found, we need to redeploy
                    return self.build_and_deploy(deployment_id)
                except Exception as e:
                    logger.error(f"Error resuming container {deployment.container_id}: {e}")
                    return {"error": f"Failed to resume container: {str(e)}"}
            
            # Update deployment status
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.started_at = datetime.now(timezone.utc)
            deployment.stopped_at = None
            self.db.commit()
            
            return {"deployment_id": deployment_id, "status": "resumed"}
            
        except Exception as e:
            logger.error(f"Failed to resume deployment {deployment_id}: {e}")
            return {"error": str(e)}

    def stop_deployment(self, deployment_id: str, timeout: int = 30) -> Dict[str, Any]:
        """Stop a deployment and wait for resources to be terminated."""
        try:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            # Stop container
            if deployment.container_id:
                try:
                    container = self.docker_client.containers.get(deployment.container_id)
                    logger.info(f"Stopping container {deployment.container_id}...")
                    
                    # Stop the container
                    container.stop(timeout=timeout)
                    logger.info(f"Container {deployment.container_id} stopped, removing...")
                    
                    # Remove the container
                    container.remove()
                    logger.info(f"Container {deployment.container_id} removed")
                    
                    # Wait for container to be fully removed
                    import time
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        try:
                            # Try to get the container - if it doesn't exist, it's been removed
                            self.docker_client.containers.get(deployment.container_id)
                            time.sleep(0.5)  # Wait 500ms before checking again
                        except docker_errors.NotFound:
                            logger.info(f"Container {deployment.container_id} fully terminated")
                            break
                    else:
                        logger.warning(f"Container {deployment.container_id} removal timeout after {timeout}s")
                        
                except docker_errors.NotFound:
                    logger.warning(f"Container {deployment.container_id} not found")
                except Exception as e:
                    logger.error(f"Error stopping container {deployment.container_id}: {e}")
                    return {"error": f"Failed to stop container: {str(e)}"}
            
            # Update deployment status
            deployment.status = DeploymentStatus.STOPPED.value
            deployment.stopped_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return {"deployment_id": deployment_id, "status": "stopped"}
            
        except Exception as e:
            logger.error(f"Failed to stop deployment {deployment_id}: {e}")
            return {"error": str(e)}
    
    def restart_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Restart a deployment."""
        try:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            # Stop the current deployment
            stop_result = self.stop_deployment(deployment_id)
            if "error" in stop_result:
                return stop_result
            
            # Rebuild and deploy
            deploy_result = self.build_and_deploy(deployment_id)
            if "error" in deploy_result:
                return deploy_result
            
            logger.info(f"Successfully restarted deployment {deployment_id}")
            return {"deployment_id": deployment_id, "status": "restarted"}
            
        except Exception as e:
            logger.error(f"Failed to restart deployment {deployment_id}: {e}")
            return {"error": str(e)}
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status with real-time health check."""
        deployment = self.db.query(AgentDeployment).filter(
            AgentDeployment.deployment_id == deployment_id
        ).first()
        
        if not deployment:
            return {"error": "Deployment not found"}
        
        # Check container status
        container_status = None
        if deployment.container_id:
            try:
                container = self.docker_client.containers.get(deployment.container_id)
                container_status = container.status
            except docker_errors.NotFound:
                container_status = "not_found"
        
        # Perform real-time health check if deployment is running
        real_time_health = deployment.is_healthy
        if deployment.status == DeploymentStatus.RUNNING.value and deployment.proxy_endpoint:
            try:
                health_url = f"{deployment.proxy_endpoint}/health"
                response = requests.get(health_url, timeout=10)  # Increased timeout from 2 to 10 seconds
                if response.status_code == 200:
                    real_time_health = True
                    # Update database with fresh health status
                    deployment.is_healthy = True
                    deployment.health_check_failures = 0
                    deployment.last_health_check = datetime.utcnow()
                    self.db.commit()
                else:
                    real_time_health = False
                    deployment.health_check_failures += 1
                    deployment.last_health_check = datetime.utcnow()
                    self.db.commit()
            except Exception:
                # Health check failed, but don't update database on temporary failures
                real_time_health = False
        
        return {
            "deployment_id": deployment_id,
            "agent_id": deployment.agent_id,
            "hiring_id": deployment.hiring_id,
            "status": deployment.status,
            "container_status": container_status,
            "proxy_endpoint": deployment.proxy_endpoint,
            "external_port": deployment.external_port,
            "internal_port": deployment.internal_port,
            "created_at": deployment.created_at.isoformat(),
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
            "is_healthy": real_time_health,
            "health_check_failures": deployment.health_check_failures,
            "status_message": deployment.status_message
        }
    
    async def health_check(self, deployment_id: str) -> Dict[str, Any]:
        """Perform health check on deployment."""
        deployment = self.db.query(AgentDeployment).filter(
            AgentDeployment.deployment_id == deployment_id
        ).first()
        
        if not deployment:
            return {"error": "Deployment not found"}
        
        # For persistent agents, check if container is running and responsive
        if deployment.deployment_type == "persistent":
            try:
                # Check if container is running
                container = self.docker_client.containers.get(deployment.container_name)
                if container.status != "running":
                    deployment.is_healthy = False
                    deployment.health_check_failures += 1
                    deployment.last_health_check = datetime.utcnow()
                    self.db.commit()
                    return {"status": "unhealthy", "error": f"Container status: {container.status}"}
                
                # Test if container responds to docker exec
                result = container.exec_run("echo 'health_check'")
                if result.exit_code == 0:
                    deployment.is_healthy = True
                    deployment.health_check_failures = 0
                    deployment.last_health_check = datetime.utcnow()
                    self.db.commit()
                    return {"status": "healthy"}
                else:
                    deployment.is_healthy = False
                    deployment.health_check_failures += 1
                    deployment.last_health_check = datetime.utcnow()
                    self.db.commit()
                    return {"status": "unhealthy", "error": f"Exec failed with exit code: {result.exit_code}"}
                    
            except Exception as e:
                deployment.is_healthy = False
                deployment.health_check_failures += 1
                deployment.last_health_check = datetime.utcnow()
                self.db.commit()
                return {"status": "unhealthy", "error": str(e)}
        
        # For ACP agents, check HTTP endpoint
        elif deployment.proxy_endpoint:
            try:
                async with aiohttp.ClientSession() as session:
                    health_url = f"{deployment.proxy_endpoint}/health"
                    async with session.get(health_url, timeout=5) as response:
                        if response.status == 200:
                            deployment.is_healthy = True
                            deployment.health_check_failures = 0
                            deployment.last_health_check = datetime.utcnow()
                            self.db.commit()
                            return {"status": "healthy"}
                        else:
                            deployment.health_check_failures += 1
                            deployment.last_health_check = datetime.utcnow()
                            self.db.commit()
                            return {"status": "unhealthy", "http_status": response.status}
            
            except Exception as e:
                deployment.is_healthy = False
                deployment.health_check_failures += 1
                deployment.last_health_check = datetime.utcnow()
                self.db.commit()
                return {"status": "unhealthy", "error": str(e)}
        else:
            return {"error": "No proxy endpoint configured for ACP agent"}
    
    def list_deployments(self, agent_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List deployments with optional filtering and real-time health checks."""
        query = self.db.query(AgentDeployment)
        
        if agent_id:
            query = query.filter(AgentDeployment.agent_id == agent_id)
        
        if status:
            # Validate status value
            valid_statuses = [s.value for s in DeploymentStatus]
            if status not in valid_statuses:
                raise ValueError(f"Invalid status: {status}. Valid statuses: {valid_statuses}")
            query = query.filter(AgentDeployment.status == status)
        
        deployments = query.order_by(AgentDeployment.created_at.desc()).all()
        
        result = []
        for deployment in deployments:
            # Perform real-time health check for running deployments
            real_time_health = deployment.is_healthy
            if deployment.status == DeploymentStatus.RUNNING.value:
                # For persistent agents, check container status
                if deployment.deployment_type == "persistent":
                    try:
                        container = self.docker_client.containers.get(deployment.container_name)
                        if container.status == "running":
                            # Test if container responds to docker exec
                            exec_result = container.exec_run("echo 'health_check'")
                            if exec_result.exit_code == 0:
                                real_time_health = True
                                deployment.is_healthy = True
                                deployment.health_check_failures = 0
                                deployment.last_health_check = datetime.utcnow()
                            else:
                                real_time_health = False
                                deployment.health_check_failures += 1
                                deployment.last_health_check = datetime.utcnow()
                        else:
                            real_time_health = False
                            deployment.health_check_failures += 1
                            deployment.last_health_check = datetime.utcnow()
                    except Exception:
                        # Health check failed, but don't update database on temporary failures
                        real_time_health = False
                
                # For ACP agents, check HTTP endpoint
                elif deployment.proxy_endpoint:
                    try:
                        health_url = f"{deployment.proxy_endpoint}/health"
                        response = requests.get(health_url, timeout=1)  # Quick timeout for list
                        if response.status_code == 200:
                            real_time_health = True
                            # Update database with fresh health status
                            deployment.is_healthy = True
                            deployment.health_check_failures = 0
                            deployment.last_health_check = datetime.utcnow()
                        else:
                            real_time_health = False
                            deployment.health_check_failures += 1
                            deployment.last_health_check = datetime.utcnow()
                    except Exception:
                        # Health check failed, but don't update database on temporary failures
                        real_time_health = False
            
            result.append({
                "deployment_id": deployment.deployment_id,
                "agent_id": deployment.agent_id,
                "hiring_id": deployment.hiring_id,
                "status": deployment.status,
                "proxy_endpoint": deployment.proxy_endpoint,
                "created_at": deployment.created_at.isoformat(),
                "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
                "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
                "is_healthy": real_time_health
            })
        
        # Commit any health check updates
        self.db.commit()
        
        return result

    # =============================================================================
    # PERSISTENT AGENT OPERATIONS
    # =============================================================================

    def _get_agent_config_from_files(self, agent_id: str) -> Dict[str, Any]:
        """Get agent configuration from config.json file."""
        from ..models.agent_file import AgentFile
        
        config_file = self.db.query(AgentFile).filter(
            AgentFile.agent_id == agent_id,
            AgentFile.file_path == 'config.json'
        ).first()
        
        if not config_file:
            raise Exception("Agent configuration file not found")
        
        import json
        return json.loads(config_file.file_content)

    async def execute_persistent_agent(self, deployment_id: str, input_data: Dict[str, Any], execution_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a persistent agent in its container via docker exec (non-blocking)."""
        try:
            # Get deployment information
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            if deployment.status != DeploymentStatus.RUNNING.value:
                return {"error": "Deployment is not running"}
            
            # Get agent configuration to determine entry point and class
            from ..models.agent import Agent
            agent = self.db.query(Agent).filter(Agent.id == deployment.agent_id).first()
            if not agent:
                return {"error": "Agent not found"}
            
            # Get agent configuration from config.json file
            try:
                agent_config = self._get_agent_config_from_files(deployment.agent_id)
                entry_point = agent_config.get('entry_point')
                agent_class = agent_config.get('agent_class')
                
                if not entry_point:
                    return {"error": "Agent configuration missing 'entry_point' in config.json"}
                if not agent_class:
                    return {"error": "Agent configuration missing 'agent_class' in config.json"}
                    
            except Exception as e:
                return {"error": f"Failed to get agent configuration: {str(e)}"}
            
            # Start execution in background task
            asyncio.create_task(
                self._execute_persistent_agent_background(deployment_id, input_data, entry_point, agent_class, execution_id)
            )
            
            logger.info(f"🚀 Started background execution for deployment {deployment_id}, execution_id: {execution_id}")
            
            return {
                "status": "started",
                "message": "Execution started in background",
                "execution_id": execution_id
            }
                
        except Exception as e:
            logger.error(f"Error starting persistent agent execution: {e}")
            return {"error": str(e)}

    async def _execute_persistent_agent_background(self, deployment_id: str, input_data: Dict[str, Any], entry_point: str, agent_class: str, execution_id: Optional[str] = None):
        """Background task to execute persistent agent."""
        try:
            # Execute in container - use centralized container naming
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                logger.error(f"Deployment not found for background execution: {deployment_id}")
                return
            
            container_name = generate_container_name(deployment)
            exec_input = {
                "operation": "execute",
                "input": input_data,
                "entry_point": entry_point,
                "agent_class": agent_class
            }
            
            # Run the blocking operation in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._execute_in_container, 
                container_name, 
                exec_input
            )
            
            logger.info(f"✅ Background execution completed for deployment {deployment_id}")
            
            # Update execution status if execution_id is provided
            if execution_id:
                await self._update_execution_status(execution_id, result)
            
        except Exception as e:
            logger.error(f"Error in background execution for deployment {deployment_id}: {e}")
            # Update execution status to failed if execution_id is provided
            if execution_id:
                await self._update_execution_status(execution_id, {"error": str(e)}, status="failed")
    
    async def _update_execution_status(self, execution_id: str, result: Dict[str, Any], status: str = "completed"):
        """Update execution status in the database."""
        try:
            from ..models.execution import Execution, ExecutionStatus
            from ..database.config import get_session
            
            # Create a new session for this update
            session = get_session()
            try:
                execution = session.query(Execution).filter(Execution.execution_id == execution_id).first()
                if execution:
                    if status == "completed":
                        execution.status = ExecutionStatus.COMPLETED.value
                        execution.output_data = result.get("result", {})
                        execution.container_logs = result.get("container_logs", "")
                        execution.completed_at = datetime.utcnow()
                        if execution.started_at:
                            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
                        logger.info(f"✅ Updated execution {execution_id} status to COMPLETED")
                    elif status == "failed":
                        execution.status = ExecutionStatus.FAILED.value
                        execution.error_message = result.get("error", "Execution failed")
                        execution.container_logs = result.get("container_logs", "")
                        execution.completed_at = datetime.utcnow()
                        if execution.started_at:
                            execution.execution_time = (execution.completed_at - execution.started_at).total_seconds()
                        logger.error(f"❌ Updated execution {execution_id} status to FAILED: {result.get('error')}")
                    
                    session.commit()
                    logger.info(f"📝 Execution {execution_id} status updated to {status}")
                else:
                    logger.warning(f"Execution {execution_id} not found for status update")
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error updating execution {execution_id} status: {e}")

    def initialize_persistent_agent(self, deployment_id: str, init_config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize a persistent agent in its container via docker exec."""
        try:
            # Get deployment information
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            if deployment.status != DeploymentStatus.RUNNING.value:
                return {"error": "Deployment is not running"}
            
            # Get agent configuration to determine entry point and class
            from ..models.agent import Agent
            agent = self.db.query(Agent).filter(Agent.id == deployment.agent_id).first()
            if not agent:
                return {"error": "Agent not found"}
            
            # Get agent configuration from config.json file
            try:
                agent_config = self._get_agent_config_from_files(deployment.agent_id)
                entry_point = agent_config.get('entry_point')
                agent_class = agent_config.get('agent_class')
                
                if not entry_point:
                    return {"error": "Agent configuration missing 'entry_point' in config.json"}
                if not agent_class:
                    return {"error": "Agent configuration missing 'agent_class' in config.json"}
                    
            except Exception as e:
                return {"error": f"Failed to get agent configuration: {str(e)}"}
            
            # Execute in container - use centralized container naming
            container_name = generate_container_name(deployment)
            exec_input = {
                "operation": "initialize",
                "input": init_config,
                "entry_point": entry_point,
                "agent_class": agent_class
            }
            
            result = self._execute_in_container(container_name, exec_input)
            
            if result.get("status") == "success":
                # Update hiring state in database
                try:
                    hiring = self.db.query(Hiring).filter(Hiring.id == deployment.hiring_id).first()
                    if hiring:
                        hiring.state = {
                            'status': 'ready',
                            'config': init_config,
                            'state_data': result.get("result", {}),
                            'created_at': time.time(),
                            'last_accessed': time.time(),
                            'execution_count': 0
                        }
                        self.db.commit()
                        logger.info(f"Updated hiring state for hiring {deployment.hiring_id}")
                except Exception as e:
                    logger.error(f"Failed to update hiring state: {e}")
                
                return {
                    "status": "success",
                    "result": result.get("result", {}),
                    "container_logs": result.get("container_logs", "")
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Initialization failed"),
                    "container_logs": result.get("container_logs", "")
                }
                
        except Exception as e:
            logger.error(f"Error initializing persistent agent: {e}")
            return {"error": str(e)}

    def cleanup_persistent_agent(self, deployment_id: str) -> Dict[str, Any]:
        """Clean up a persistent agent in its container via docker exec (non-blocking)."""
        try:
            # Get deployment information
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            if deployment.status != DeploymentStatus.RUNNING.value:
                return {"error": "Deployment is not running"}
            
            # Get agent configuration to determine entry point and class
            from ..models.agent import Agent
            agent = self.db.query(Agent).filter(Agent.id == deployment.agent_id).first()
            if not agent:
                return {"error": "Agent not found"}
            
            # Get agent configuration from config.json file
            try:
                agent_config = self._get_agent_config_from_files(deployment.agent_id)
                entry_point = agent_config.get('entry_point', 'persistent_rag_agent.py')
                agent_class = agent_config.get('agent_class', 'RAGAgent')
            except Exception as e:
                return {"error": f"Failed to get agent configuration: {str(e)}"}
            
            # Execute in container - use centralized container naming
            container_name = generate_container_name(deployment)
            exec_input = {
                "operation": "cleanup",
                "entry_point": entry_point,
                "agent_class": agent_class
            }
            
            # Start cleanup in a separate thread to avoid blocking
            import threading
            cleanup_thread = threading.Thread(
                target=self._execute_in_container,
                args=(container_name, exec_input)
            )
            cleanup_thread.start()
            
            # Return immediately - cleanup is running in background
            return {
                "status": "success",
                "message": "Cleanup started in background",
                "deployment_id": deployment_id
            }
                
        except Exception as e:
            logger.error(f"Error cleaning up persistent agent: {e}")
            return {"error": str(e)}

    def _execute_in_container(self, container_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command in a persistent agent container via Docker exec."""
        try:
            container = self.docker_client.containers.get(container_name)
            
            # Determine operation type
            operation = input_data.get('operation', 'execute')
            
            if operation == 'initialize':
                # Execute initialization
                python_script = f"""
import json
import sys
import os
import tempfile
import time
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

print("Starting initialization script...", file=sys.stderr)
sys.path.append('/app')

# Capture both stdout and stderr
stdout_capture = StringIO()
stderr_capture = StringIO()

try:
    print("Importing agent class...", file=sys.stderr)
    # Import the agent class
    from {input_data.get('entry_point', '').replace('.py', '')} import {input_data.get('agent_class', '')}
    print("Agent class imported successfully", file=sys.stderr)

    print("Creating agent instance...", file=sys.stderr)
    # Create agent instance and initialize
    agent = {input_data.get('agent_class', '')}()
    print("Agent instance created", file=sys.stderr)
    
    # Convert JavaScript boolean values to Python booleans
    def convert_js_to_python(obj):
        if isinstance(obj, dict):
            return {{key: convert_js_to_python(value) for key, value in obj.items()}}
        elif isinstance(obj, list):
            return [convert_js_to_python(item) for item in obj]
        elif obj == "true":
            return True
        elif obj == "false":
            return False
        elif obj == "null":
            return None
        else:
            return obj
    
    # Convert input data
    input_data = {repr(input_data.get('input', {}))}
    converted_input = convert_js_to_python(input_data)
    
    print("Starting agent initialization...", file=sys.stderr)
    start_time = time.time()
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        result = agent.initialize(converted_input)
    end_time = time.time()
    print(f"Agent initialization completed in {{end_time - start_time:.2f}} seconds", file=sys.stderr)

    print("Saving agent state...", file=sys.stderr)
    # Save state to file (only essential data, not the full agent object)
    state_data = {{
        'initialized': True,
        'config': converted_input,
        'agent_state': agent._state if hasattr(agent, '_state') else {{}}
    }}
    
    with open('/app/state/agent_state.json', 'w') as f:
        json.dump(state_data, f)
    print("Agent state saved", file=sys.stderr)

    print("Writing result to temp file...", file=sys.stderr)
    # Write result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"status": "success", "result": result}}, f)
    print("Result written to temp file", file=sys.stderr)
        
except Exception as e:
    print(f"Exception during initialization: {{str(e)}}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    # Capture any exceptions in stderr
    stderr_capture.write(f"Error: {{str(e)}}\\n")
    # Write error result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"status": "error", "error": str(e)}}, f)

print("Writing captured output to temp files...", file=sys.stderr)
# Write captured output to temp files
with open('/tmp/agent_stdout.txt', 'w') as f:
    f.write(stdout_capture.getvalue())

with open('/tmp/agent_stderr.txt', 'w') as f:
    f.write(stderr_capture.getvalue())

print("Initialization script completed", file=sys.stderr)
"""
                exec_command = ["python", "-c", python_script]
                
            elif operation == 'execute':
                # Execute the agent
                python_script = f"""
import json
import sys
import os
import tempfile
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

sys.path.append('/app')

# Capture both stdout and stderr
stdout_capture = StringIO()
stderr_capture = StringIO()

try:
    # Load state from file
    try:
        with open('/app/state/agent_state.json', 'r') as f:
            state_data = json.load(f)
    except FileNotFoundError:
        raise Exception("Agent not initialized. Call initialize first.")

    # Import the agent class
    from {input_data.get('entry_point', '').replace('.py', '')} import {input_data.get('agent_class', '')}

    # Create agent instance and restore state
    agent = {input_data.get('agent_class', '')}()
    agent._initialized = state_data.get('initialized', False)
    agent._state = state_data.get('agent_state', {{}})

    # Convert JavaScript boolean values to Python booleans
    def convert_js_to_python(obj):
        if isinstance(obj, dict):
            return {{key: convert_js_to_python(value) for key, value in obj.items()}}
        elif isinstance(obj, list):
            return [convert_js_to_python(item) for item in obj]
        elif obj == "true":
            return True
        elif obj == "false":
            return False
        elif obj == "null":
            return None
        else:
            return obj
    
    # Convert input data
    input_data = {repr(input_data.get('input', {}))}
    converted_input = convert_js_to_python(input_data)

    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        result = agent.execute(converted_input)

    # Save updated state
    state_data['agent_state'] = agent._state if hasattr(agent, '_state') else {{}}
    with open('/app/state/agent_state.json', 'w') as f:
        json.dump(state_data, f)

    # Write result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"status": "success", "result": result}}, f)
        
except Exception as e:
    # Capture any exceptions in stderr
    stderr_capture.write(f"Error: {{str(e)}}\\n")
    # Write error result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"status": "error", "error": str(e)}}, f)

# Write captured output to temp files
with open('/tmp/agent_stdout.txt', 'w') as f:
    f.write(stdout_capture.getvalue())

with open('/tmp/agent_stderr.txt', 'w') as f:
    f.write(stderr_capture.getvalue())
"""
                exec_command = ["python", "-c", python_script]
                
            elif operation == 'cleanup':
                # Cleanup the agent
                python_script = f"""
import json
import sys
import os
import tempfile
import time
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

sys.path.append('/app')

# Capture both stdout and stderr
stdout_capture = StringIO()
stderr_capture = StringIO()

try:
    # Load state from file
    try:
        with open('/app/state/agent_state.json', 'r') as f:
            state_data = json.load(f)
    except FileNotFoundError:
        # No state to cleanup
        result = {{"status": "cleaned_up", "message": "No agent state to cleanup"}}
    else:
        # Import the agent class
        from {input_data.get('entry_point', '').replace('.py', '')} import {input_data.get('agent_class', '')}

        # Create agent instance and restore state
        agent = {input_data.get('agent_class', '')}()
        agent._initialized = state_data.get('initialized', False)
        agent._state = state_data.get('agent_state', {{}})

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = agent.cleanup()

        # Remove state file
        os.remove('/app/state/agent_state.json')

    # Write result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"status": "success", "result": result}}, f)
        
except Exception as e:
    # Capture any exceptions in stderr
    stderr_capture.write(f"Error: {{str(e)}}\\n")
    # Write error result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"status": "error", "error": str(e)}}, f)

# Write captured output to temp files
with open('/tmp/agent_stdout.txt', 'w') as f:
    f.write(stdout_capture.getvalue())

with open('/tmp/agent_stderr.txt', 'w') as f:
    f.write(stderr_capture.getvalue())
"""
                exec_command = ["python", "-c", python_script]
            else:
                return {"status": "error", "error": f"Unknown operation: {operation}"}
            
            # Execute command in container
            exec_result = container.exec_run(exec_command)
            
            # Read captured stdout and stderr
            stdout_result = container.exec_run(cmd=["cat", "/tmp/agent_stdout.txt"])
            stderr_result = container.exec_run(cmd=["cat", "/tmp/agent_stderr.txt"])
            
            # Combine logs
            stdout_logs = stdout_result.output.decode() if stdout_result.exit_code == 0 else ""
            stderr_logs = stderr_result.output.decode() if stderr_result.exit_code == 0 else ""
            
            # Create combined logs
            container_logs = ""
            if stdout_logs:
                container_logs += f"=== STDOUT ===\n{stdout_logs}\n"
            if stderr_logs:
                container_logs += f"=== STDERR ===\n{stderr_logs}\n"
            if exec_result.output:
                container_logs += f"=== CONTAINER OUTPUT ===\n{exec_result.output.decode()}\n"
            
            if exec_result.exit_code != 0:
                error_msg = f"Container execution failed (exit code: {exec_result.exit_code}): {exec_result.output.decode()}"
                logger.error(f"Container execution failed for {container_name}: {error_msg}")
                logger.error(f"Container logs: {container_logs}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "container_logs": container_logs
                }
            
            # Read result from temp file
            read_result = container.exec_run(cmd=["cat", "/tmp/agent_result.json"])
            if read_result.exit_code != 0:
                error_msg = f"Failed to read result file (exit code: {read_result.exit_code}): {read_result.output.decode()}"
                logger.error(f"Failed to read result file from {container_name}: {error_msg}")
                return {
                    "status": "error", 
                    "error": error_msg,
                    "container_logs": container_logs
                }
            
            result_json = read_result.output.decode().strip()
            result_data = json.loads(result_json)
            
            # Add container logs to the result data
            result_data["container_logs"] = container_logs
            
            # Log the container logs for debugging
            logger.info(f"Container logs captured for {container_name}: {len(container_logs)} characters")
            if container_logs:
                logger.info(f"First 200 chars of logs: {container_logs[:200]}...")
            
            # Clean up temp files
            container.exec_run(cmd=["rm", "-f", "/tmp/agent_result.json", "/tmp/agent_stdout.txt", "/tmp/agent_stderr.txt"])
            
            return result_data
                
        except Exception as e:
            logger.error(f"Error executing in container: {e}")
            return {"status": "error", "error": str(e)} 