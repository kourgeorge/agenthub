"""Function deployment service for managing function agent Docker containers."""

import os
import json
import shutil
import logging
import docker
from docker import errors as docker_errors
import uuid
import asyncio
import tempfile
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import socket

from .env_service import EnvironmentService
from ..models.agent import Agent, AgentType
from ..models.hiring import Hiring
from ..models.deployment import AgentDeployment, DeploymentStatus
from .container_utils import generate_container_name, generate_docker_image_name
from .resource_limits import get_agent_resource_limits, to_docker_config

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
            
            # Generate deployment ID - use Docker-compliant format
            user_id = hiring.user_id or "anon"
            # Use underscores and lowercase for better Docker compatibility
            safe_agent_id = str(agent.id).lower().replace('-', '_')
            deployment_id = f"func_{safe_agent_id}_{hiring_id}_{uuid.uuid4().hex[:8]}"
            
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
    
    async def build_and_deploy_function(self, deployment_id: str) -> Dict[str, Any]:
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
            
            # Build Docker image using centralized utility
            user_id = deployment.hiring.user_id or "anon"
            hiring_id = deployment.hiring_id
            deployment_uuid = deployment_id.split('_')[-1]  # Get the UUID part
            image_name = generate_docker_image_name("func", user_id, agent.id, hiring_id, deployment_uuid)
            image = await self._build_function_docker_image(deploy_dir, image_name)
            
            # Update deployment with image info
            deployment.docker_image = image_name
            deployment.status = DeploymentStatus.DEPLOYING.value
            self.db.commit()
            
            # Deploy container
            container = await self._deploy_function_container(deployment, image_name)
            
            # Update deployment with container info
            deployment.container_id = container.id
            deployment.container_name = container.name
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.started_at = datetime.now(timezone.utc)
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
    
    async def execute_in_container(self, deployment_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function in the deployed container asynchronously."""
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
            
            # Get agent details
            from ..models.agent import Agent
            agent = self.db.query(Agent).filter(Agent.id == deployment.agent_id).first()
            if not agent:
                return {"error": "Agent not found"}
            
            # Prepare input data
            input_json = json.dumps(input_data)
            
            # Get execution_id from input_data if available
            execution_id = input_data.get("execution_id")
            
            # Prepare environment variables
            env_vars = {
                "AGENTHUB_SERVER_URL": "http://host.docker.internal:8002"
            }
            
            # Add execution_id to environment if available
            if execution_id:
                env_vars["AGENTHUB_EXECUTION_ID"] = execution_id
            
            # Execute the function in the container
            # Parse entry point to get file and function name
            entry_point = agent.entry_point
            if ':' in entry_point:
                file_name, function_name = entry_point.split(':', 1)
            else:
                file_name = entry_point
                function_name = 'main'
            
            # Remove .py extension if present for import
            module_name = file_name.replace('.py', '')
            
            # Create a Python script that captures both stdout and stderr
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
    # Ensure we're importing the Python file, not any JSON files
    if os.path.exists('/app/{module_name}.py'):
        from {module_name} import {function_name}
        
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
        
        # Parse and convert input data
        input_data = json.loads({repr(input_json)})
        converted_input = convert_js_to_python(input_data)
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Try different calling patterns to handle various function signatures
            try:
                # First try calling with converted input directly
                result = {function_name}(converted_input)
            except TypeError:
                try:
                    # If that fails, try calling with keyword argument 'config'
                    result = {function_name}(config=converted_input)
                except TypeError:
                    try:
                        # If that fails, try calling with both input_data and config
                        result = {function_name}(converted_input, converted_input)
                    except TypeError:
                        try:
                            # If that also fails, try calling with keyword arguments
                            if isinstance(converted_input, dict):
                                result = {function_name}(**converted_input)
                            else:
                                # If that also fails, try calling with no arguments
                                result = {function_name}()
                        except TypeError:
                            # Last resort: try calling with no arguments
                            result = {function_name}()
        
        # Write result to temp file
        with open('/tmp/agent_result.json', 'w') as f:
            json.dump(result, f)
    else:
        raise ImportError(f"Module {{module_name}} not found")
        
except Exception as e:
    # Capture any exceptions in stderr
    stderr_capture.write(f"Error: {{str(e)}}\\n")
    # Write error result to temp file
    with open('/tmp/agent_result.json', 'w') as f:
        json.dump({{"error": str(e)}}, f)

# Write captured output to temp files
with open('/tmp/agent_stdout.txt', 'w') as f:
    f.write(stdout_capture.getvalue())

with open('/tmp/agent_stderr.txt', 'w') as f:
    f.write(stderr_capture.getvalue())
"""
            
            logger.info(f"Executing function in container {container.id} with environment: {env_vars}")
            
            # Execute the script in the container
            exec_result = container.exec_run(
                cmd=["python", "-c", python_script],
                environment=env_vars
            )
            
            logger.info(f"Container execution completed with exit code: {exec_result.exit_code}")
            
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
            
            # Log detailed execution information for debugging
            logger.info(f"Function execution details for {deployment_id}:")
            logger.info(f"  Exit code: {exec_result.exit_code}")
            logger.info(f"  Stdout length: {len(stdout_logs)}")
            logger.info(f"  Stderr length: {len(stderr_logs)}")
            if stderr_logs:
                logger.info(f"  Stderr content: {stderr_logs[:500]}...")
            
            if exec_result.exit_code != 0:
                error_msg = f"Container execution failed with exit code {exec_result.exit_code}: {exec_result.output.decode()}"
                logger.error(f"Function execution failed: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "container_logs": container_logs
                }
            
            # Read result from temp file
            read_result = container.exec_run(cmd=["cat", "/tmp/agent_result.json"])
            if read_result.exit_code != 0:
                error_msg = f"Failed to read result file: {read_result.output.decode()}"
                logger.error(f"Failed to read result file: {error_msg}")
                return {
                    "status": "error", 
                    "error": error_msg,
                    "container_logs": container_logs
                }
            
            result_json = read_result.output.decode().strip()
            try:
                result_data = json.loads(result_json)
                logger.info(f"Function execution result: {result_data}")
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse result JSON: {e}. Raw result: {result_json[:200]}..."
                logger.error(f"JSON parsing error: {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "container_logs": container_logs
                }
            
            # Clean up temp files
            container.exec_run(cmd=["rm", "-f", "/tmp/agent_result.json", "/tmp/agent_stdout.txt", "/tmp/agent_stderr.txt"])
            
            return {
                "status": "success",
                "output": result_data,
                "execution_time": None,  # Could be added if needed
                "container_logs": container_logs
            }
                
        except Exception as e:
            logger.error(f"Failed to execute function in container {deployment_id}: {e}")
            return {"error": str(e)}
    
    def get_function_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status for a function agent."""
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
        
        return {
            "deployment_id": deployment_id,
            "agent_id": deployment.agent_id,
            "hiring_id": deployment.hiring_id,
            "status": deployment.status,
            "container_status": container_status,
            "container_id": deployment.container_id,
            "container_name": deployment.container_name,
            "created_at": deployment.created_at.isoformat(),
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
            "status_message": deployment.status_message
        }
    
    def suspend_function_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Suspend a function deployment by stopping the container but keeping it."""
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
                    container.stop(timeout=10)
                    logger.info(f"Suspended function container {deployment.container_id}")
                except Exception as e:
                    if "not found" in str(e).lower():
                        logger.warning(f"Container {deployment.container_id} not found")
                    else:
                        logger.error(f"Error suspending container: {e}")
            
            # Update deployment status
            deployment.status = DeploymentStatus.STOPPED.value
            deployment.stopped_at = datetime.now(timezone.utc)
            self.db.commit()
            
            return {"status": "success", "message": "Deployment suspended"}
            
        except Exception as e:
            logger.error(f"Failed to suspend deployment: {e}")
            return {"error": str(e)}

    def resume_function_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Resume a suspended function deployment by starting the stopped container."""
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
                    container.start()
                    logger.info(f"Resumed function container {deployment.container_id}")
                except Exception as e:
                    if "not found" in str(e).lower():
                        logger.warning(f"Container {deployment.container_id} not found - may need to redeploy")
                        # If container not found, we need to redeploy
                        return self.build_and_deploy_function(deployment_id)
                    else:
                        logger.error(f"Error resuming container: {e}")
                        return {"error": str(e)}
            
            # Update deployment status
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.started_at = datetime.now(timezone.utc)
            deployment.stopped_at = None
            self.db.commit()
            
            return {"status": "success", "message": "Deployment resumed"}
            
        except Exception as e:
            logger.error(f"Failed to resume deployment: {e}")
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
            deployment.stopped_at = datetime.now(timezone.utc)
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
                    # Use entry point to determine file name
                    entry_file = agent.entry_point.split(':')[0] if agent.entry_point else "agent_code.py"
                    agent_file = deploy_dir / entry_file
                    with open(agent_file, 'w') as f:
                        f.write(agent.code)
                    logger.info(f"Extracted legacy agent code to {entry_file}")
                elif agent.file_path and os.path.exists(agent.file_path):
                    # Use entry point to determine file name
                    entry_file = agent.entry_point.split(':')[0] if agent.entry_point else "agent_code.py"
                    agent_file = deploy_dir / entry_file
                    with open(agent.file_path, 'r') as src, open(agent_file, 'w') as dst:
                        dst.write(src.read())
                    logger.info(f"Copied agent file: {agent.file_path} to {entry_file}")
                else:
                    raise ValueError("No agent code found")
            
            # Create requirements.txt if agent has requirements (including empty list)
            if agent.requirements is not None:
                requirements_file = deploy_dir / "requirements.txt"
                with open(requirements_file, 'w') as f:
                    for req in agent.requirements:
                        f.write(f"{req}\n")
                logger.info("Created requirements.txt")
            
            # Create merged .env file with external API keys
            agent_env_path = self._get_agent_env_path(agent)
            merged_env_path = self.env_service.create_merged_env_file(
                agent_env_path=agent_env_path,
                output_path=str(deploy_dir / ".env")
            )
            logger.info(f"Created merged .env file for function deployment: {merged_env_path}")
            
            # Create Dockerfile for function agents
            dockerfile_path = deploy_dir / "Dockerfile"
            with open(dockerfile_path, 'w') as f:
                f.write(self._generate_function_dockerfile())
            logger.info("Created Dockerfile for function deployment")
            
        except Exception as e:
            logger.error(f"Failed to extract agent code: {e}")
            raise
    
    async def _build_function_docker_image(self, deploy_dir: Path, image_name: str):
        """Build Docker image for the function agent asynchronously."""
        logger.info(f"Building function Docker image {image_name}")
        
        try:
            # Run Docker build in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            image, logs = await loop.run_in_executor(
                None,
                lambda: self.docker_client.images.build(
                    path=str(deploy_dir),
                    tag=image_name,
                    rm=True,
                    forcerm=True
                )
            )
            
            # Log build output
            for log in logs:
                if isinstance(log, dict) and 'stream' in log:
                    stream_content = log['stream']
                    if isinstance(stream_content, str):
                        logger.info(f"Build: {stream_content.strip()}")
            
            logger.info(f"Function Docker image {image_name} built successfully")
            return image
            
        except Exception as e:
            logger.error(f"Failed to build function Docker image: {e}")
            raise
    


    async def _deploy_function_container(self, deployment: AgentDeployment, image_name: str):
        """Deploy Docker container for the function agent asynchronously."""
        user_id = deployment.hiring.user_id or "anon"
        
        # Use centralized container naming
        container_name = generate_container_name(deployment, "func")
        
        logger.info(f"Deploying function container {container_name}")
        
        # Container configuration for function agents
        container_config = {
            "image": image_name,
            "name": container_name,
            "environment": deployment.environment_vars,
            "detach": True,
            "restart_policy": {"Name": "unless-stopped"},
            "working_dir": "/app",
            "labels": {
                "monitoring": "true",
                "agent_type": "function",
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
            container = await loop.run_in_executor(
                None,
                lambda: self.docker_client.containers.run(**container_config)
            )
            
            # Update deployment with container info
            deployment.container_id = container.id
            deployment.container_name = container_name
            deployment.status = DeploymentStatus.RUNNING.value
            deployment.deployed_at = datetime.now(timezone.utc)
            deployment.is_healthy = True
            deployment.health_check_failures = 0
            deployment.last_health_check = datetime.now(timezone.utc)
            
            self.db.commit()
            
            logger.info(f"Function container {container_name} deployed successfully with ID {container.id}")
            return container
            
        except Exception as e:
            logger.error(f"Failed to deploy function container {container_name}: {e}")
            deployment.status = DeploymentStatus.FAILED.value
            deployment.error_message = str(e)
            self.db.commit()
            raise

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