"""Execution service for managing agent execution."""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.execution import Execution, ExecutionStatus
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..database.config import get_session
from .agent_runtime import AgentRuntimeService, RuntimeStatus

logger = logging.getLogger(__name__)


class ExecutionCreateRequest(BaseModel):
    """Request model for creating an execution."""
    agent_id: int
    hiring_id: Optional[int] = None
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
        
        execution = Execution(
            agent_id=execution_data.agent_id,
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
                runtime_result = self._execute_acp_server_agent(agent, execution.input_data or {})
            else:
                # Handle traditional function-based agents
                runtime_service = AgentRuntimeService()
                runtime_result = runtime_service.execute_agent(
                    agent_id=execution.agent_id,
                    input_data=execution.input_data or {},
                    agent_code=agent.code if hasattr(agent, 'code') else None,
                    agent_file_path=agent.file_path if hasattr(agent, 'file_path') else None
                )
            
            # Process runtime result
            if runtime_result.status == RuntimeStatus.COMPLETED:
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
    
    def _execute_acp_server_agent(self, agent: Agent, input_data: Dict[str, Any]):
        """Execute an ACP server agent using its compatibility mode."""
        import tempfile
        import subprocess
        import sys
        import json
        import time
        from .agent_runtime import RuntimeResult, RuntimeStatus
        
        start_time = time.time()
        
        try:
            # Create temporary execution directory
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Executing ACP server agent {agent.id} in compatibility mode")
                
                # Write agent code to file
                if not agent.code:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error="No agent code available",
                        execution_time=time.time() - start_time
                    )
                
                agent_file = f"{temp_dir}/agent_code.py"
                with open(agent_file, 'w') as f:
                    f.write(agent.code)
                
                # Create execution script that calls the agent's main function
                exec_script = f"""
import sys
import json
import logging
sys.path.insert(0, '{temp_dir}')

# Suppress logging during execution to avoid interfering with JSON output
logging.getLogger().setLevel(logging.ERROR)

try:
    from agent_code import main
    input_data = {json.dumps(input_data)}
    config_data = {{}}
    result = main(input_data, config_data)
    print(json.dumps(result))
except Exception as e:
    error_result = {{"status": "error", "error": str(e)}}
    print(json.dumps(error_result))
"""
                
                # Execute the script
                process = subprocess.run(
                    [sys.executable, '-c', exec_script],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )
                
                execution_time = time.time() - start_time
                
                if process.returncode == 0:
                    # Parse the output as JSON
                    try:
                        result_data = json.loads(process.stdout.strip())
                        return RuntimeResult(
                            status=RuntimeStatus.COMPLETED,
                            output=json.dumps(result_data),
                            execution_time=execution_time
                        )
                    except json.JSONDecodeError:
                        return RuntimeResult(
                            status=RuntimeStatus.FAILED,
                            error=f"Invalid JSON output: {process.stdout}",
                            execution_time=execution_time
                        )
                else:
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=process.stderr or f"Agent execution failed with code {process.returncode}",
                        execution_time=execution_time
                    )
                    
        except subprocess.TimeoutExpired:
            return RuntimeResult(
                status=RuntimeStatus.TIMEOUT,
                error="Agent execution timeout",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"ACP server agent execution error: {str(e)}",
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