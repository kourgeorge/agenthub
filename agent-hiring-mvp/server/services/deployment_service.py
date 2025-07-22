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
from datetime import datetime
from pathlib import Path
import tempfile
import socket

from sqlalchemy.orm import Session
from ..models.agent import Agent, AgentType
from ..models.hiring import Hiring
from ..models.deployment import AgentDeployment, DeploymentStatus
from .env_service import EnvironmentService

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
            
            # Generate deployment ID with agent type
            user_id = hiring.user_id or "anon"
            agent_type = agent.agent_type
            deployment_id = f"{agent_type}-user-{user_id}-agent-{agent.id}-hire-{hiring_id}-{uuid.uuid4().hex[:8]}"
            
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
    
    def build_and_deploy(self, deployment_id: str) -> Dict[str, Any]:
        """Build Docker image and deploy the agent."""
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
            
            # Build Docker image
            user_id = deployment.hiring.user_id or "anon"
            agent_type = agent.agent_type
            image_name = f"{agent_type}-user-{user_id}-agent-{agent.id}-hire-{deployment.hiring_id}:{deployment_id}"
            image = self._build_docker_image(deploy_dir, image_name)
            
            # Update deployment with image info
            deployment.docker_image = image_name
            deployment.status = DeploymentStatus.DEPLOYING.value
            self.db.commit()
            
            # Deploy container
            container = self._deploy_container(deployment, image_name)
            
            # Update deployment with container info
            deployment.container_id = container.id
            deployment.container_name = container.name
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.started_at = datetime.utcnow()
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
        for agent_file in agent.files:
            # Create directory structure if needed
            file_path = deploy_dir / agent_file.file_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            file_path.write_text(agent_file.file_content, encoding='utf-8')
            
            logger.info(f"Extracted file: {agent_file.file_path}")
        
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
    
    def _build_docker_image(self, deploy_dir: Path, image_name: str):
        """Build Docker image for the agent."""
        logger.info(f"Building Docker image {image_name}")
        
        image, logs = self.docker_client.images.build(
            path=str(deploy_dir),
            tag=image_name,
            rm=True,
            forcerm=True
        )
        
        # Log build output
        for log in logs:
            if isinstance(log, dict) and 'stream' in log:
                stream_content = log['stream']
                if isinstance(stream_content, str):
                    logger.info(f"Build: {stream_content.strip()}")
        
        return image
    
    def _deploy_container(self, deployment: AgentDeployment, image_name: str):
        """Deploy Docker container for the agent."""
        user_id = deployment.hiring.user_id or "anon"
        agent_type = deployment.deployment_type or "function"
        container_name = f"{agent_type}-user-{user_id}-agent-{deployment.agent_id}-hire-{deployment.hiring_id}-{deployment.deployment_id}"
        
        logger.info(f"Deploying container {container_name}")
        
        # Container configuration
        container_config = {
            "image": image_name,
            "name": container_name,
            "environment": deployment.environment_vars,
            "detach": True
        }
        
        # Add port mapping for server-based agents (acp only)
        if agent_type == "acp" and deployment.external_port:
            container_config["ports"] = {f"{deployment.internal_port}/tcp": deployment.external_port}
            container_config["restart_policy"] = {"Name": "unless-stopped"}
        elif agent_type == "persistent":
            # Persistent agents stay running and need restart policy
            container_config["restart_policy"] = {"Name": "unless-stopped"}
        else:
            # Function agents don't need restart policy since they run once
            container_config["restart_policy"] = {"Name": "no"}
        
        # Add any additional deployment configuration
        if deployment.deployment_config:
            container_config.update(deployment.deployment_config)
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config)
        
        logger.info(f"Container {container_name} started with ID {container.id}")
        
        return container
    
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
            deployment.stopped_at = datetime.utcnow()
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
            deployment.started_at = datetime.utcnow()
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
            deployment.stopped_at = datetime.utcnow()
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
                response = requests.get(health_url, timeout=2)
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
    
    def list_deployments(self, agent_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
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

    def _get_agent_config_from_files(self, agent_id: int) -> Dict[str, Any]:
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

    def execute_persistent_agent(self, deployment_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a persistent agent in its container via docker exec."""
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
            
            # Execute in container
            container_name = f"{deployment.deployment_type}-user-{deployment.hiring.user_id or 'anon'}-agent-{deployment.agent_id}-hire-{deployment.hiring_id}-{deployment.deployment_id}"
            exec_input = {
                "operation": "execute",
                "input": input_data,
                "entry_point": entry_point,
                "agent_class": agent_class
            }
            
            result = self._execute_in_container(container_name, exec_input)
            
            if result.get("status") == "success":
                return {
                    "status": "success",
                    "result": result.get("result", {})
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Execution failed")
                }
                
        except Exception as e:
            logger.error(f"Error executing persistent agent: {e}")
            return {"error": str(e)}

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
                entry_point = agent_config.get('entry_point', 'persistent_rag_agent.py')
                agent_class = agent_config.get('agent_class', 'RAGAgent')
            except Exception as e:
                return {"error": f"Failed to get agent configuration: {str(e)}"}
            
            # Execute in container
            container_name = f"{deployment.deployment_type}-user-{deployment.hiring.user_id or 'anon'}-agent-{deployment.agent_id}-hire-{deployment.hiring_id}-{deployment.deployment_id}"
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
                    "result": result.get("result", {})
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Initialization failed")
                }
                
        except Exception as e:
            logger.error(f"Error initializing persistent agent: {e}")
            return {"error": str(e)}

    def cleanup_persistent_agent(self, deployment_id: str) -> Dict[str, Any]:
        """Clean up a persistent agent in its container via docker exec."""
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
            
            # Execute in container
            container_name = f"{deployment.deployment_type}-user-{deployment.hiring.user_id or 'anon'}-agent-{deployment.agent_id}-hire-{deployment.hiring_id}-{deployment.deployment_id}"
            exec_input = {
                "operation": "cleanup",
                "entry_point": entry_point,
                "agent_class": agent_class
            }
            
            result = self._execute_in_container(container_name, exec_input)
            
            if result.get("status") == "success":
                return {
                    "status": "success",
                    "result": result.get("result", {})
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Cleanup failed")
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
    from {input_data.get('entry_point', 'persistent_rag_agent').replace('.py', '')} import {input_data.get('agent_class', 'RAGAgent')}
    print("Agent class imported successfully", file=sys.stderr)

    print("Creating agent instance...", file=sys.stderr)
    # Create agent instance and initialize
    agent = {input_data.get('agent_class', 'RAGAgent')}()
    print("Agent instance created", file=sys.stderr)
    
    print("Starting agent initialization...", file=sys.stderr)
    start_time = time.time()
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        result = agent.initialize({json.dumps(input_data.get('input', {}))})
    end_time = time.time()
    print(f"Agent initialization completed in {{end_time - start_time:.2f}} seconds", file=sys.stderr)

    print("Saving agent state...", file=sys.stderr)
    # Save state to file (only essential data, not the full agent object)
    state_data = {{
        'initialized': True,
        'config': {input_data.get('input', {})},
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
    from {input_data.get('entry_point', 'persistent_rag_agent').replace('.py', '')} import {input_data.get('agent_class', 'RAGAgent')}

    # Create agent instance and restore state
    agent = {input_data.get('agent_class', 'RAGAgent')}()
    agent._initialized = state_data.get('initialized', False)
    agent._state = state_data.get('agent_state', {{}})

    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        result = agent.execute({json.dumps(input_data.get('input', {}))})

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
        from {input_data.get('entry_point', 'persistent_rag_agent').replace('.py', '')} import {input_data.get('agent_class', 'RAGAgent')}

        # Create agent instance and restore state
        agent = {input_data.get('agent_class', 'RAGAgent')}()
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
            
            # Clean up temp files
            container.exec_run(cmd=["rm", "-f", "/tmp/agent_result.json", "/tmp/agent_stdout.txt", "/tmp/agent_stderr.txt"])
            
            return result_data
                
        except Exception as e:
            logger.error(f"Error executing in container: {e}")
            return {"status": "error", "error": str(e)} 