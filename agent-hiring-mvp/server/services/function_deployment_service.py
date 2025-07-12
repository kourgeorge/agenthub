"""Function deployment service for managing function agent Docker containers."""

import os
import json
import shutil
import logging
import docker
import uuid
import asyncio
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import socket

from ..models.agent import Agent, AgentType
from ..models.hiring import Hiring
from ..models.deployment import AgentDeployment, DeploymentStatus

logger = logging.getLogger(__name__)


class FunctionDeploymentService:
    """Service for managing function agent Docker deployments."""
    
    def __init__(self, db):
        self.db = db
        self.docker_client = docker.from_env()
        
        # Use cross-platform temporary directory
        temp_base = os.getenv("AGENTHUB_TEMP_DIR") or tempfile.gettempdir()
        self.deployment_dir = Path(temp_base) / "function_deployments"
        self.deployment_dir.mkdir(parents=True, exist_ok=True)
    
    def create_function_deployment(self, hiring_id: int) -> Dict[str, Any]:
        """Create a new deployment for a hired function agent."""
        try:
            # Get hiring and agent information
            hiring = self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
            if not hiring:
                return {"error": "Hiring not found"}
            
            agent = hiring.agent
            if not agent:
                return {"error": "Agent not found"}
            
            # Check if agent is function type
            if agent.agent_type != AgentType.FUNCTION.value:
                return {"error": "Agent is not a function type"}
            
            # Check if deployment already exists
            existing_deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring_id
            ).first()
            
            if existing_deployment:
                return {"error": "Deployment already exists", "deployment_id": existing_deployment.deployment_id}
            
            # Generate deployment ID
            user_id = hiring.user_id or "anon"
            deployment_id = f"func-user-{user_id}-agent-{agent.id}-hire-{hiring_id}-{uuid.uuid4().hex[:8]}"
            
            # Create deployment record
            deployment = AgentDeployment(
                agent_id=agent.id,
                hiring_id=hiring_id,
                deployment_id=deployment_id,
                external_port=None,  # Function agents don't need external ports
                status=DeploymentStatus.PENDING.value,
                proxy_endpoint=None,  # Function agents don't have proxy endpoints
                environment_vars={
                    "DEPLOYMENT_ID": deployment_id,
                    "AGENT_ID": str(agent.id),
                    "HIRING_ID": str(hiring_id),
                    "USER_ID": str(user_id),
                    "AGENT_TYPE": "function"
                }
            )
            
            self.db.add(deployment)
            self.db.commit()
            
            logger.info(f"Created function deployment {deployment_id} for agent {agent.id}")
            
            return {
                "deployment_id": deployment_id,
                "status": "created",
                "agent_type": "function"
            }
            
        except Exception as e:
            logger.error(f"Failed to create function deployment: {e}")
            return {"error": str(e)}
    
    def build_and_deploy_function(self, deployment_id: str) -> Dict[str, Any]:
        """Build Docker image and deploy the function agent."""
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
            self._extract_function_agent_code(agent, deploy_dir)
            
            # Build Docker image
            user_id = deployment.hiring.user_id or "anon"
            image_name = f"func-user-{user_id}-agent-{agent.id}-hire-{deployment.hiring_id}:{deployment_id}"
            image = self._build_function_docker_image(deploy_dir, image_name)
            
            # Update deployment with image info
            deployment.docker_image = image_name
            deployment.status = DeploymentStatus.DEPLOYING.value
            self.db.commit()
            
            # Deploy container
            container = self._deploy_function_container(deployment, image_name)
            
            # Update deployment with container info
            deployment.container_id = container.id
            deployment.container_name = container.name
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.started_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Successfully deployed function agent {agent.id} in container {container.name}")
            
            return {
                "status": "success",
                "deployment_id": deployment_id,
                "container_id": container.id,
                "container_name": container.name,
                "image_name": image_name
            }
            
        except Exception as e:
            logger.error(f"Failed to build and deploy function agent: {e}")
            if deployment:
                deployment.status = DeploymentStatus.FAILED.value
                deployment.status_message = str(e)
                self.db.commit()
            return {"error": str(e)}
    
    def execute_in_container(self, deployment_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function in the deployed container."""
        try:
            # Get deployment
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            if deployment.status != DeploymentStatus.RUNNING.value:
                return {"error": f"Deployment is not running (status: {deployment.status})"}
            
            # Get container
            container = self.docker_client.containers.get(deployment.container_id)
            
            # Prepare input data
            input_json = json.dumps(input_data)
            
            # Execute the function in the container
            exec_result = container.exec_run(
                cmd=["python", "-c", f"""
import json
import sys
sys.path.append('/app')
from agent_code import main
result = main({input_json}, {{}})
print(json.dumps(result))
"""],
                environment={
                    "PYTHONPATH": "/app",
                    "INPUT_DATA": input_json
                }
            )
            
            if exec_result.exit_code == 0:
                try:
                    # Parse the output as JSON
                    output_data = json.loads(exec_result.output.decode().strip())
                    return {
                        "status": "success",
                        "output": output_data,
                        "execution_time": None  # Could be added if needed
                    }
                except json.JSONDecodeError:
                    # Fallback to raw output
                    return {
                        "status": "success",
                        "output": exec_result.output.decode().strip()
                    }
            else:
                error_output = exec_result.output.decode().strip()
                return {
                    "status": "error",
                    "error": f"Container execution failed: {error_output}",
                    "exit_code": exec_result.exit_code
                }
                
        except Exception as e:
            logger.error(f"Failed to execute in container: {e}")
            return {"error": str(e)}
    
    def stop_function_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Stop and remove a function deployment."""
        try:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.deployment_id == deployment_id
            ).first()
            
            if not deployment:
                return {"error": "Deployment not found"}
            
            # Stop container if running
            if deployment.container_id:
                try:
                    container = self.docker_client.containers.get(deployment.container_id)
                    container.stop(timeout=10)
                    container.remove()
                    logger.info(f"Stopped and removed container {deployment.container_id}")
                except Exception as e:
                    if "not found" in str(e).lower():
                        logger.warning(f"Container {deployment.container_id} not found")
                    else:
                        logger.error(f"Error stopping container: {e}")
            
            # Update deployment status
            deployment.status = DeploymentStatus.STOPPED.value
            deployment.stopped_at = datetime.utcnow()
            self.db.commit()
            
            return {"status": "success", "message": "Deployment stopped"}
            
        except Exception as e:
            logger.error(f"Failed to stop deployment: {e}")
            return {"error": str(e)}
    
    def _extract_function_agent_code(self, agent: Agent, deploy_dir: Path):
        """Extract function agent code to deployment directory."""
        try:
            # Get agent files
            from ..models.agent_file import AgentFile
            agent_files = self.db.query(AgentFile).filter(
                AgentFile.agent_id == agent.id
            ).all()
            
            if agent_files:
                # Multi-file approach
                for file_record in agent_files:
                    file_path = deploy_dir / file_record.file_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_record.file_content)
                    
                    logger.info(f"Extracted file: {file_record.file_path}")
            else:
                # Legacy single-file approach
                if agent.code:
                    agent_file = deploy_dir / "agent_code.py"
                    with open(agent_file, 'w') as f:
                        f.write(agent.code)
                    logger.info("Extracted legacy agent code")
                elif agent.file_path and os.path.exists(agent.file_path):
                    agent_file = deploy_dir / "agent_code.py"
                    with open(agent.file_path, 'r') as src, open(agent_file, 'w') as dst:
                        dst.write(src.read())
                    logger.info(f"Copied agent file: {agent.file_path}")
                else:
                    raise ValueError("No agent code found")
            
            # Create requirements.txt if agent has requirements
            if agent.requirements:
                requirements_file = deploy_dir / "requirements.txt"
                with open(requirements_file, 'w') as f:
                    for req in agent.requirements:
                        f.write(f"{req}\n")
                logger.info("Created requirements.txt")
            
        except Exception as e:
            logger.error(f"Failed to extract agent code: {e}")
            raise
    
    def _build_function_docker_image(self, deploy_dir: Path, image_name: str):
        """Build Docker image for function agent."""
        try:
            # Create Dockerfile
            dockerfile_content = self._generate_function_dockerfile()
            dockerfile_path = deploy_dir / "Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(dockerfile_content)
            
            # Build image
            logger.info(f"Building Docker image: {image_name}")
            image, build_logs = self.docker_client.images.build(
                path=str(deploy_dir),
                tag=image_name,
                rm=True,
                dockerfile="Dockerfile"
            )
            
            logger.info(f"Successfully built image: {image_name}")
            return image
            
        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            raise
    
    def _deploy_function_container(self, deployment: AgentDeployment, image_name: str):
        """Deploy Docker container for the function agent."""
        user_id = deployment.hiring.user_id or "anon"
        container_name = f"func-user-{user_id}-agent-{deployment.agent_id}-hire-{deployment.hiring_id}-{deployment.deployment_id}"
        
        logger.info(f"Deploying function container {container_name}")
        
        # Container configuration for function agents
        container_config = {
            "image": image_name,
            "name": container_name,
            "environment": deployment.environment_vars,
            "detach": True,
            "restart_policy": {"Name": "unless-stopped"},
            "working_dir": "/app"
        }
        
        # Create and start container
        container = self.docker_client.containers.run(**container_config)
        
        logger.info(f"Function container {container_name} started with ID {container.id}")
        return container
    
    def _generate_function_dockerfile(self) -> str:
        """Generate Dockerfile for function agents."""
        return """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Keep container running for function execution
CMD ["tail", "-f", "/dev/null"]
""" 