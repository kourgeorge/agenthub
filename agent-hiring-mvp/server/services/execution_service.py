"""Execution service for managing agent execution."""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.execution import Execution, ExecutionStatus
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..models.agent_file import AgentFile
from ..database.config import get_session
from .agent_runtime import AgentRuntimeService, RuntimeStatus, RuntimeResult

logger = logging.getLogger(__name__)


class ExecutionCreateRequest(BaseModel):
    """Request model for creating an execution."""
    hiring_id: int  # Now required
    user_id: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None


class ExecutionService:
    """Service for managing agent execution."""
    
    def __init__(self, db=None):
        if db is None:
            self.db = get_session()
        else:
            self.db = db
    
    def create_execution(self, execution_data: ExecutionCreateRequest) -> Execution:
        """Create a new execution record."""
        execution_id = str(uuid.uuid4())
        
        # Validate hiring exists and is active
        hiring = self.db.query(Hiring).filter(Hiring.id == execution_data.hiring_id).first()
        if not hiring:
            raise ValueError("Hiring not found")
        
        if hiring.status != "active":
            raise ValueError(f"Hiring is not active (status: {hiring.status})")
        
        execution = Execution(
            agent_id=hiring.agent_id,  # Get agent_id from hiring
            hiring_id=execution_data.hiring_id,
            user_id=execution_data.user_id,
            status=ExecutionStatus.PENDING.value,
            input_data=execution_data.input_data or {},
            execution_id=execution_id,
        )
        
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        logger.info(f"Created execution: {execution_id}")
        return execution
    
    def get_execution(self, execution_id: str) -> Optional[Execution]:
        """Get an execution by ID."""
        return self.db.query(Execution).filter(Execution.execution_id == execution_id).first()
    
    def update_execution_status(self, execution_id: str, status: ExecutionStatus, 
                               output_data: Optional[Dict[str, Any]] = None,
                               error_message: Optional[str] = None) -> Optional[Execution]:
        """Update execution status."""
        execution = self.get_execution(execution_id)
        if not execution:
            return None
        
        execution.status = status.value
        execution.updated_at = datetime.utcnow()
        
        if status == ExecutionStatus.RUNNING:
            execution.started_at = datetime.utcnow()
        elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]:
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds() * 1000
                execution.duration_ms = int(duration)
        
        if output_data is not None:
            execution.output_data = output_data
        
        if error_message is not None:
            execution.error_message = error_message
        
        self.db.commit()
        self.db.refresh(execution)
        
        logger.info(f"Updated execution {execution_id} status to {status.value}")
        return execution
    
    def get_agent_executions(self, agent_id: int, limit: int = 100) -> list[Execution]:
        """Get executions for an agent."""
        return (
            self.db.query(Execution)
            .filter(Execution.agent_id == agent_id)
            .order_by(Execution.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_user_executions(self, user_id: int, limit: int = 100) -> list[Execution]:
        """Get executions for a user."""
        return (
            self.db.query(Execution)
            .filter(Execution.user_id == user_id)
            .order_by(Execution.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_hiring_executions(self, hiring_id: int, limit: int = 100) -> list[Execution]:
        """Get executions for a hiring."""
        return (
            self.db.query(Execution)
            .filter(Execution.hiring_id == hiring_id)
            .order_by(Execution.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def execute_agent(self, execution_id: str) -> Dict[str, Any]:
        """Execute an agent using the real runtime service."""
        execution = self.get_execution(execution_id)
        if not execution:
            return {"status": "error", "message": "Execution not found"}
        
        # Update status to running
        self.update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        try:
            # Get agent details
            agent = self.db.query(Agent).filter(Agent.id == execution.agent_id).first()
            if not agent:
                raise Exception("Agent not found")
            
            # Check agent type and handle accordingly
            agent_type = getattr(agent, 'agent_type', 'function')
            
            if agent_type == 'acp_server':
                # Handle ACP server agents
                runtime_result = self._execute_acp_server_agent(agent, execution.input_data or {}, execution_id)
            else:
                # Handle function-based agents with Docker deployment
                runtime_result = self._execute_function_agent(agent, execution.input_data or {}, execution_id)
            
            # Process runtime result
            if runtime_result.status == RuntimeStatus.COMPLETED:
                # Check if the output is already a JSON object (dict)
                if isinstance(runtime_result.output, dict):
                    # Agent returned a proper JSON object, use it directly
                    output_data = runtime_result.output
                else:
                    # Agent returned a string, wrap it in the standard format
                    output_data = {
                        "output": runtime_result.output,
                        "execution_time": runtime_result.execution_time,
                        "status": "success"
                    }
                
                self.update_execution_status(execution_id, ExecutionStatus.COMPLETED, output_data)
                
                return {
                    "status": "success",
                    "execution_id": execution_id,
                    "result": output_data,
                    "execution_time": runtime_result.execution_time
                }
            
            elif runtime_result.status == RuntimeStatus.TIMEOUT:
                error_msg = "Execution timeout"
                self.update_execution_status(execution_id, ExecutionStatus.TIMEOUT, error_message=error_msg)
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": error_msg
                }
            
            elif runtime_result.status == RuntimeStatus.SECURITY_VIOLATION:
                error_msg = f"Security violation: {runtime_result.error}"
                self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg)
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": error_msg
                }
            
            else:  # FAILED or other status
                error_msg = runtime_result.error or "Execution failed"
                self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg)
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": error_msg
                }
        
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}"
            self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg)
            return {
                "status": "error",
                "execution_id": execution_id,
                "error": error_msg
            }
    
    def _get_agent_files(self, agent_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get all files for an agent."""
        agent_files = self.db.query(AgentFile).filter(AgentFile.agent_id == agent_id).all()
        if agent_files:
            return [file.to_dict() for file in agent_files]
        return None
    
    def _execute_function_agent(self, agent: Agent, input_data: Dict[str, Any], execution_id: str):
        """Execute a function agent using Docker deployment."""
        try:
            # Get the execution to find the hiring_id
            execution = self.get_execution(execution_id)
            if not execution:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="Execution not found"
                )
            
            # Get the deployment for this specific hiring
            from ..models.deployment import AgentDeployment, DeploymentStatus
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == execution.hiring_id,
                AgentDeployment.status == DeploymentStatus.RUNNING.value
            ).first()
            
            if deployment:
                # Use Docker deployment if available
                from .function_deployment_service import FunctionDeploymentService
                deployment_service = FunctionDeploymentService(self.db)
                
                result = deployment_service.execute_in_container(deployment.deployment_id, input_data)
                
                if result.get("status") == "success":
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=result.get("output"),
                        execution_time=result.get("execution_time")
                    )
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=result.get("error", "Unknown error")
                    )
            else:
                # Fallback to traditional runtime service
                runtime_service = AgentRuntimeService()
                
                # Try to get agent files (new multi-file approach)
                agent_files = self._get_agent_files(agent.id)
                
                if agent_files:
                    # Use new multi-file approach
                    return runtime_service.execute_agent(
                        agent_id=agent.id,
                        input_data=input_data,
                        agent_files=agent_files,
                        entry_point=agent.entry_point
                    )
                else:
                    # Fallback to legacy single-file approach
                    return runtime_service.execute_agent(
                        agent_id=agent.id,
                        input_data=input_data,
                        agent_code=agent.code if hasattr(agent, 'code') else None,
                        agent_file_path=agent.file_path if hasattr(agent, 'file_path') else None,
                        entry_point=agent.entry_point
                    )
                
        except Exception as e:
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Function agent execution error: {str(e)}"
            )
    
    def _execute_acp_server_agent(self, agent: Agent, input_data: Dict[str, Any], execution_id: str):
        """Execute an ACP server agent by making HTTP requests to the running server."""
        import requests
        import json
        import time
        from .agent_runtime import RuntimeResult, RuntimeStatus
        from ..models.deployment import AgentDeployment
        from ..models.hiring import Hiring
        
        start_time = time.time()
        
        try:
            # Get the execution to find the hiring_id
            execution = self.get_execution(execution_id)
            if not execution:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="Execution not found",
                    execution_time=time.time() - start_time
                )
            
            # Get the hiring associated with this execution
            hiring = self.db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
            if not hiring:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="No active hiring found for this agent",
                    execution_time=time.time() - start_time
                )
            
            # Get the deployment associated with this hiring
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id,
                AgentDeployment.status == "running"
            ).first()
            
            if not deployment:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="No running deployment found for this agent",
                    execution_time=time.time() - start_time
                )
            
            # Determine the endpoint URL
            if deployment.proxy_endpoint:
                base_url = deployment.proxy_endpoint.rstrip('/')
            elif deployment.external_port:
                base_url = f"http://localhost:{deployment.external_port}"
            else:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="No endpoint available for ACP agent",
                    execution_time=time.time() - start_time
                )
            
            # Prepare the request payload for the ACP server
            # ACP agents expect a specific format for chat messages
            chat_payload = {
                "message": input_data.get("message", str(input_data)),
                "session_id": input_data.get("session_id"),
                "context": input_data.get("context", {})
            }
            
            # Make HTTP request to the ACP server's chat endpoint
            chat_url = f"{base_url}/chat"
            logger.info(f"Making request to ACP agent at {chat_url}")
            
            response = requests.post(
                chat_url,
                json=chat_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result_data = response.json()
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=json.dumps(result_data),
                        execution_time=execution_time
                    )
                except json.JSONDecodeError:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=f"Invalid JSON response from ACP agent: {response.text}",
                        execution_time=execution_time
                    )
            else:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"ACP agent returned status {response.status_code}: {response.text}",
                    execution_time=execution_time
                )
        
        except Exception as e:
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"ACP execution error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def get_execution_stats(self, agent_id: Optional[int] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get execution statistics."""
        query = self.db.query(Execution)
        
        if agent_id:
            query = query.filter(Execution.agent_id == agent_id)
        
        if user_id:
            query = query.filter(Execution.user_id == user_id)
        
        total_executions = query.count()
        completed_executions = query.filter(Execution.status == ExecutionStatus.COMPLETED.value).count()
        failed_executions = query.filter(Execution.status == ExecutionStatus.FAILED.value).count()
        
        return {
            "total_executions": total_executions,
            "completed_executions": completed_executions,
            "failed_executions": failed_executions,
            "success_rate": (completed_executions / total_executions * 100) if total_executions > 0 else 0,
        } 