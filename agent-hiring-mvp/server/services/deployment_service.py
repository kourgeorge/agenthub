"""Deployment service for managing ACP agent Docker containers."""

import os
import json
import shutil
import logging
import docker
import uuid
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import tempfile
import socket

from sqlalchemy.orm import Session
from ..models.agent import Agent, AgentType
from ..models.hiring import Hiring
from ..models.deployment import AgentDeployment, DeploymentStatus

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
        """Create a new deployment for a hired ACP agent."""
        try:
            # Get hiring and agent information
            hiring = self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
            if not hiring:
                return {"error": "Hiring not found"}
            
            agent = hiring.agent
            if not agent:
                return {"error": "Agent not found"}
            
            # Check if agent is ACP server type
            if agent.agent_type != AgentType.ACP_SERVER.value:
                return {"error": "Agent is not an ACP server type"}
            
            # Check if deployment already exists
            existing_deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring_id
            ).first()
            
            if existing_deployment:
                return {"error": "Deployment already exists", "deployment_id": existing_deployment.deployment_id}
            
            # Generate deployment ID
            deployment_id = f"agent-{agent.id}-{uuid.uuid4().hex[:8]}"
            
            # Get available port
            external_port = self.get_available_port()
            
            # Create deployment record
            deployment = AgentDeployment(
                agent_id=agent.id,
                hiring_id=hiring_id,
                deployment_id=deployment_id,
                external_port=external_port,
                status=DeploymentStatus.PENDING.value,
                proxy_endpoint=f"http://{self.server_hostname}:{external_port}",
                environment_vars={
                    "PORT": "8001",
                    "DEPLOYMENT_ID": deployment_id,
                    "AGENT_ID": str(agent.id),
                    "HIRING_ID": str(hiring_id)
                }
            )
            
            self.db.add(deployment)
            self.db.commit()
            
            logger.info(f"Created deployment {deployment_id} for agent {agent.id}")
            
            return {
                "deployment_id": deployment_id,
                "status": "created",
                "external_port": external_port,
                "proxy_endpoint": deployment.proxy_endpoint
            }
            
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
            image_name = f"agent-{agent.id}:{deployment_id}"
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
        elif agent.code:
            # Write code directly to file with UTF-8 encoding
            main_file = deploy_dir / "main.py"
            main_file.write_text(agent.code, encoding='utf-8')
        else:
            raise ValueError("No agent code available")
        
        # Create basic requirements.txt if not exists
        requirements_file = deploy_dir / "requirements.txt"
        if not requirements_file.exists():
            requirements = agent.requirements or []
            requirements_file.write_text("\n".join(requirements), encoding='utf-8')
        
        # Create basic Dockerfile if not exists
        dockerfile = deploy_dir / "Dockerfile"
        if not dockerfile.exists():
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
        container_name = f"agent-{deployment.agent_id}-{deployment.deployment_id}"
        
        logger.info(f"Deploying container {container_name}")
        
        # Container configuration
        container_config = {
            "image": image_name,
            "name": container_name,
            "ports": {f"{deployment.internal_port}/tcp": deployment.external_port},
            "environment": deployment.environment_vars,
            "detach": True,
            "restart_policy": {"Name": "unless-stopped"}
        }
        
        # Add any additional deployment configuration
        if deployment.deployment_config:
            container_config.update(deployment.deployment_config)
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config)
        
        logger.info(f"Container {container_name} started with ID {container.id}")
        
        return container
    
    def stop_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Stop a deployment."""
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
                    container.stop()
                    container.remove()
                    logger.info(f"Stopped container {deployment.container_id}")
                except docker.errors.NotFound:
                    logger.warning(f"Container {deployment.container_id} not found")
            
            # Update deployment status
            deployment.status = DeploymentStatus.STOPPED.value
            deployment.stopped_at = datetime.utcnow()
            self.db.commit()
            
            return {"deployment_id": deployment_id, "status": "stopped"}
            
        except Exception as e:
            logger.error(f"Failed to stop deployment {deployment_id}: {e}")
            return {"error": str(e)}
    
    def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status."""
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
            except docker.errors.NotFound:
                container_status = "not_found"
        
        return {
            "deployment_id": deployment_id,
            "status": deployment.status,
            "container_status": container_status,
            "proxy_endpoint": deployment.proxy_endpoint,
            "created_at": deployment.created_at.isoformat(),
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "is_healthy": deployment.is_healthy,
            "health_check_failures": deployment.health_check_failures
        }
    
    async def health_check(self, deployment_id: str) -> Dict[str, Any]:
        """Perform health check on deployment."""
        deployment = self.db.query(AgentDeployment).filter(
            AgentDeployment.deployment_id == deployment_id
        ).first()
        
        if not deployment:
            return {"error": "Deployment not found"}
        
        if not deployment.proxy_endpoint:
            return {"error": "No proxy endpoint configured"}
        
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
    
    def list_deployments(self, agent_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List deployments with optional filtering."""
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
        
        return [
            {
                "deployment_id": deployment.deployment_id,
                "agent_id": deployment.agent_id,
                "hiring_id": deployment.hiring_id,
                "status": deployment.status,
                "proxy_endpoint": deployment.proxy_endpoint,
                "created_at": deployment.created_at.isoformat(),
                "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
                "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
                "is_healthy": deployment.is_healthy
            }
            for deployment in deployments
        ] 