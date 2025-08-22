"""Execution service for managing agent execution."""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.execution import Execution, ExecutionStatus
from ..models.agent import Agent, AgentStatus
from ..models.hiring import Hiring
from ..models.agent_file import AgentFile
from ..database.config import get_session
from .persistent_agent_runtime import RuntimeStatus, RuntimeResult
from .persistent_agent_runtime import PersistentAgentRuntimeService
from .resource_manager import ResourceManager
from .json_schema_validation_service import JSONSchemaValidationService

logger = logging.getLogger(__name__)


class ExecutionCreateRequest(BaseModel):
    """Request model for creating an execution."""
    hiring_id: int  # Now required
    user_id: int  # Now required - comes from authentication
    input_data: Optional[Dict[str, Any]] = None
    execution_type: str = "run"  # "initialize", "run", or "cleanup"


class ExecutionService:
    """Service for managing agent execution.
    
    This service uses dual database sessions:
    - self.db: User's authenticated session for API operations
    - self.system_db: System session for background updates (bypasses auth)
    
    This design allows the service to:
    1. Respect user authentication for execution initiation
    2. Update execution status in the background without auth requirements
    3. Maintain proper separation between user and system operations
    """
    
    def __init__(self, db=None):
        if db is None:
            # Create a new database session that won't be closed by FastAPI
            self.db = get_session()
            self._owns_session = True
        else:
            # Use the provided session (from API layer)
            self.db = db
            self._owns_session = False
        
        # Create a separate system database session for background updates
        # This bypasses user authentication requirements for database operations
        self.system_db = get_session()
        self._owns_system_session = True
        
        # Initialize resource manager for usage tracking
        self.resource_manager = ResourceManager(self.db)
        
        # Initialize persistent agent runtime
        self.persistent_runtime = PersistentAgentRuntimeService()
        
        # Initialize JSON Schema validation service
        self.json_schema_validator = JSONSchemaValidationService()
    
    def __del__(self):
        """Clean up database sessions if we own them."""
        if hasattr(self, '_owns_session') and self._owns_session and hasattr(self, 'db'):
            try:
                self.db.close()
            except:
                pass
        
        if hasattr(self, '_owns_system_session') and self._owns_system_session and hasattr(self, 'system_db'):
            try:
                self.system_db.close()
            except:
                pass
    
    def create_execution(self, execution_data: ExecutionCreateRequest) -> Execution:
        """Create a new execution record."""
        execution_id = str(uuid.uuid4())
        
        # Validate hiring exists
        hiring = self.db.query(Hiring).filter(Hiring.id == execution_data.hiring_id).first()
        if not hiring:
            raise ValueError("Hiring not found")
        
        # For cleanup executions, allow any hiring status
        # For other executions, require active status
        if execution_data.execution_type != "cleanup" and hiring.status != "active":
            raise ValueError(f"Hiring is not active (status: {hiring.status})")
        
        # Validate that the agent is approved
        agent = self.db.query(Agent).filter(Agent.id == hiring.agent_id).first()
        if not agent:
            raise ValueError("Agent not found")
        
        # Ensure user_id is set - it should come from the authenticated user
        if not execution_data.user_id:
            raise ValueError("User ID is required for execution creation")
        
        # Validate that the user executing is the same as the hiring user
        if execution_data.user_id != hiring.user_id:
            raise ValueError(f"User ID {execution_data.user_id} does not match hiring user ID {hiring.user_id}")
        
        # Check if agent is approved OR if the user is executing their own agent
        if agent.status != AgentStatus.APPROVED.value and agent.owner_id != execution_data.user_id:
            raise ValueError(f"Agent is not approved (status: {agent.status}) and you don't own it")
        
        execution = Execution(
            agent_id=hiring.agent_id,  # Get agent_id from hiring
            hiring_id=execution_data.hiring_id,
            user_id=execution_data.user_id,
            status=ExecutionStatus.PENDING.value,
            execution_type=execution_data.execution_type,
            input_data=execution_data.input_data or {},
            execution_id=execution_id,
        )
        
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        logger.info(f"Created execution: {execution_id} for user: {execution_data.user_id}")
        return execution
    
    def get_execution(self, execution_id: str) -> Optional[Execution]:
        """Get an execution by ID using the user's database session."""
        return self.db.query(Execution).filter(Execution.execution_id == execution_id).first()
    
    def _get_execution_system(self, execution_id: str) -> Optional[Execution]:
        """Get an execution by ID using the system database session for internal operations."""
        return self.system_db.query(Execution).filter(Execution.execution_id == execution_id).first()
    
    def update_execution_status(self, execution_id: str, status: ExecutionStatus, 
                               output_data: Optional[Dict[str, Any]] = None,
                               error_message: Optional[str] = None,
                               container_logs: Optional[str] = None) -> Optional[Execution]:
        """Update execution status and optionally set output data or error message."""

        # Use the main database session for all operations to ensure consistency
        execution = self.db.query(Execution).filter(Execution.execution_id == execution_id).first()
        if not execution:
            logger.error(f"❌ EXECUTION NOT FOUND: {execution_id}")
            return None

        old_status = execution.status
        execution.status = status.value
        
        if status == ExecutionStatus.RUNNING and not execution.started_at:
            execution.started_at = datetime.utcnow()
        elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT, ExecutionStatus.CANCELLED]:
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000)

        if output_data is not None:
            execution.output_data = output_data

        if error_message is not None:
            execution.error_message = error_message

        if container_logs is not None:
            execution.container_logs = container_logs

        try:
            # Commit using the main database session
            self.db.commit()
            logger.info(f"✅ Execution status updated: {execution_id} -> {status.value}")
        except Exception as e:
            logger.error(f"DATABASE COMMIT FAILED: {execution_id}")
            logger.error(f"   Error: {str(e)}")
            self.db.rollback()
            raise
        
        return execution
    
    def get_agent_executions(self, agent_id: str, limit: int = 100) -> list[Execution]:
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
    
    async def execute_agent(self, execution_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute an agent using the unified runtime service."""

        # Use main database session for all operations to ensure consistency
        execution = self.get_execution(execution_id)
        if not execution:
            logger.error(f"EXECUTION NOT FOUND FOR EXECUTION: {execution_id}")
            return {"status": "error", "message": "Execution not found"}
        
        # Use provided user_id or fall back to execution's user_id
        current_user_id = user_id or execution.user_id or 1

        # Start resource tracking for this execution
        await self.resource_manager.start_execution(execution_id, current_user_id)
        
        # Update status to running using main database session
        self.update_execution_status(execution_id, ExecutionStatus.RUNNING)
        logger.info(f"🚀 Execution {execution_id} started - status set to RUNNING")
        
        try:
            # Get agent details
            agent = self.db.query(Agent).filter(Agent.id == execution.agent_id).first()
            if not agent:
                raise Exception("Agent not found")
            
            logger.info(f"📋 Executing agent {agent.id} (type: {agent.agent_type}) for execution {execution_id}")
            
            # Validate input data using JSON Schema if available
            if execution.input_data and agent.has_json_schema:
                try:
                    validated_input = self.json_schema_validator.validate_input(execution.input_data, agent)
                    logger.info(f"✅ Input validation passed for agent {agent.id}")
                except ValueError as e:
                    logger.error(f"❌ Input validation failed for agent {agent.id}: {e}")
                    self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=f"Input validation failed: {e}")
                    return {
                        "status": "error",
                        "execution_id": execution_id,
                        "error": f"Input validation failed: {e}"
                    }
            
            # Get agent configuration
            agent_config = self._get_agent_config(agent)
            requires_initialization = agent_config.get('requires_initialization', False)
            
            # Check agent type and execute accordingly
            agent_type = getattr(agent, 'agent_type', 'function')
            logger.info(f"🔍 Agent type detected: {agent_type}")
            
            if agent_type == 'acp_server':
                # Handle ACP server agents
                logger.info(f"🌐 Executing ACP server agent {agent.id}")
                runtime_result = await self._execute_acp_server_agent(agent, execution.input_data or {}, execution_id)
            elif agent_type == 'persistent':
                # Handle persistent agents
                logger.info(f"🔄 Executing persistent agent {agent.id}")
                # Check if agent has a Docker deployment for this hiring
                deployment = self._get_active_deployment_for_hiring(execution.hiring_id)
                if deployment:
                    # Use Docker-based persistent agent
                    from .deployment_service import DeploymentService
                    deployment_service = DeploymentService(self.db)
                    
                    # Track execution time
                    import time
                    start_time = time.time()
                    
                    result = await deployment_service.execute_persistent_agent(deployment.deployment_id, execution.input_data or {})
                    
                    execution_time = time.time() - start_time
                    logger.info(f"⏱️ Persistent agent execution completed in {execution_time:.2f}s")
                    
                    if result.get("status") == "success":
                        runtime_result = RuntimeResult(
                            status=RuntimeStatus.COMPLETED,
                            output=result.get("result", {}),
                            execution_time=execution_time
                        )
                    else:
                        runtime_result = RuntimeResult(
                            status=RuntimeStatus.FAILED,
                            error=result.get("error", "Execution failed"),
                            execution_time=execution_time
                        )
                else:
                    # Persistent agents require Docker deployment - no in-process fallback
                    return {
                        "status": "error",
                        "execution_id": execution_id,
                        "error": f"Persistent agent {agent.id} requires Docker deployment. No deployment found for hiring {execution.hiring_id}."
                    }
            else:
                # Handle function agents (implicit initialization)
                logger.info(f"⚙️ Executing function agent {agent.id}")
                runtime_result = await self._execute_function_agent(agent, execution.input_data or {}, execution_id)
            
            logger.info(f"✅ Execution {execution_id} completed with status: {runtime_result.status}")
            
            # End resource tracking and get usage summary
            usage_summary = await self.resource_manager.end_execution(execution_id, "completed")

            # Process runtime result
            if runtime_result.status == RuntimeStatus.COMPLETED:
                logger.info(f"🎉 Execution {execution_id} succeeded - updating status to COMPLETED")

                # Validate output data using JSON Schema if available
                if agent.has_json_schema and isinstance(runtime_result.output, dict):
                    try:
                        validated_output = self.json_schema_validator.validate_output(runtime_result.output, agent)
                        logger.info(f"✅ Output validation passed for agent {agent.id}")
                        # Use validated output as the agent's result
                        agent_output = validated_output
                    except ValueError as e:
                        logger.error(f"❌ Output validation failed for agent {agent.id}: {e}")
                        # Continue with original output but log the validation failure
                        agent_output = runtime_result.output
                        logger.warning(f"⚠️ Using unvalidated output due to validation failure: {e}")
                else:
                    # Check if the output is already a JSON object (dict)
                    if isinstance(runtime_result.output, dict):
                        # Agent returned a proper JSON object, use it directly
                        agent_output = runtime_result.output
                    else:
                        # Agent returned a string, wrap it in the standard format
                        agent_output = {
                            "output": runtime_result.output,
                            "execution_time": runtime_result.execution_time,
                            "status": "success"
                        }

                # Store the agent's output in the database
                self.update_execution_status(execution_id, ExecutionStatus.COMPLETED, agent_output, container_logs=runtime_result.container_logs)
                logger.info(f"✅ Execution {execution_id} status updated to COMPLETED in database")
                
                # Return AgentHub response with agent output and meta information
                return {
                    "status": "success",
                    "execution_id": execution_id,
                    "result": agent_output,  # Agent's output according to its outputSchema
                    "execution_time": runtime_result.execution_time,
                    "usage_summary": usage_summary,
                    "metadata": {
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_type": agent.agent_type,
                        "execution_status": "completed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "validation_status": "validated" if agent.has_json_schema else "no_schema"
                    }
                }
            
            elif runtime_result.status == RuntimeStatus.FAILED:
                logger.error(f"RUNTIME FAILED: {execution_id}")
                logger.error(f"Error: {runtime_result.error}")
                
                # End resource tracking for failed execution
                await self.resource_manager.end_execution(execution_id, "failed")
                error_msg = runtime_result.error or "Execution failed"
                
                self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg, container_logs=runtime_result.container_logs)
                logger.info(f"Execution {execution_id} status updated to FAILED in database")
                
                logger.error(f"EXECUTION FAILED: {execution_id}")
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": error_msg,
                    "metadata": {
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_type": agent.agent_type,
                        "execution_status": "failed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "error_type": "runtime_failure"
                    }
                }
            
            else:  # FAILED or other status
                logger.error(f"RUNTIME UNKNOWN STATUS: {execution_id}")
                logger.error(f"Status: {runtime_result.status}")
                logger.error(f"Error: {runtime_result.error}")
                
                # End resource tracking for failed execution
                await self.resource_manager.end_execution(execution_id, "failed")
                error_msg = runtime_result.error or "Execution failed"
                
                self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg, container_logs=runtime_result.container_logs)
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": error_msg,
                    "metadata": {
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_type": agent.agent_type,
                        "execution_status": "failed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "error_type": "unknown_status"
                    }
                }
        
        except Exception as e:
            logger.error(f"UNEXPECTED EXCEPTION IN EXECUTION: {execution_id}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception message: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            
            # End resource tracking on error
            await self.resource_manager.end_execution(execution_id, "failed")
            error_msg = f"Execution failed: {str(e)}"
            self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg)
            return {
                "status": "error",
                "execution_id": execution_id,
                "error": error_msg,
                "metadata": {
                    "agent_id": agent.id if 'agent' in locals() else None,
                    "agent_name": agent.name if 'agent' in locals() else None,
                    "agent_type": agent.agent_type if 'agent' in locals() else None,
                    "execution_status": "failed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_type": "unexpected_exception"
                }
            }
    
    def _get_agent_files(self, agent_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get all files for an agent."""
        agent_files = self.db.query(AgentFile).filter(AgentFile.agent_id == agent_id).all()
        if agent_files:
            return [file.to_dict() for file in agent_files]
        return None
    
    async def _execute_function_agent(self, agent: Agent, input_data: Dict[str, Any], execution_id: str):
        """Execute a function agent using Docker deployment asynchronously."""
        try:
            # Get the execution to find the hiring_id
            execution = self.get_execution(execution_id)
            if not execution:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="Execution not found"
                )
            
            # Add execution_id to input_data for resource tracking
            enhanced_input_data = input_data.copy()
            enhanced_input_data["execution_id"] = execution_id
            
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
                
                logger.info(f"Executing function agent {agent.id} in container {deployment.deployment_id}")
                result = await deployment_service.execute_in_container(deployment.deployment_id, enhanced_input_data)
                logger.info(f"Container execution result: {result}")
                
                # Extract container logs
                container_logs = result.get("container_logs", "")
                logger.info(f"Container logs: {container_logs[:200]}...")  # First 200 chars
                
                if result.get("status") == "success":
                    # Function deployment service returns "result" field, not "output"
                    output_data = result.get("result") or result.get("output")
                    execution_time = result.get("execution_time")

                    # If no execution time provided, use a default
                    if execution_time is None:
                        execution_time = 0.0
                    
                    return RuntimeResult(
                        status=RuntimeStatus.COMPLETED,
                        output=output_data,
                        execution_time=execution_time,
                        container_logs=container_logs
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Function execution failed: {error_msg}")
                    return RuntimeResult(
                        status=RuntimeStatus.FAILED,
                        error=error_msg,
                        container_logs=container_logs
                    )
            else:
                # Function agents require Docker deployment - no subprocess fallback
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error=f"Function agent {agent.id} requires Docker deployment. No deployment found for hiring {execution.hiring_id}."
                )
                
        except Exception as e:
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"Function agent execution error: {str(e)}"
            )
    
    async def _execute_acp_server_agent(self, agent: Agent, input_data: Dict[str, Any], execution_id: str):
        """Execute an ACP server agent via HTTP request asynchronously."""
        import time
        start_time = time.time()
        
        try:
            # Get deployment for this agent
            from ..models.deployment import AgentDeployment
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.agent_id == agent.id
            ).first()
            
            if not deployment:
                return RuntimeResult(
                    status=RuntimeStatus.FAILED,
                    error="No deployment found for ACP agent",
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
            
            # Make HTTP request to the ACP server's chat endpoint asynchronously
            chat_url = f"{base_url}/chat"
            logger.info(f"Making async request to ACP agent at {chat_url}")
            
            import aiohttp
            import asyncio
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    chat_url,
                    json=chat_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    execution_time = time.time() - start_time
                    
                    if response.status == 200:
                        response_data = await response.json()
                        logger.info(f"ACP agent execution completed successfully in {execution_time:.2f}s")
                        
                        return RuntimeResult(
                            status=RuntimeStatus.COMPLETED,
                            output=response_data,
                            execution_time=execution_time
                        )
                    else:
                        error_text = await response.text()
                        logger.error(f"ACP agent returned error status {response.status}: {error_text}")
                        
                        return RuntimeResult(
                            status=RuntimeStatus.FAILED,
                            error=f"ACP agent error: {response.status} - {error_text}",
                            execution_time=execution_time
                        )
                        
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(f"ACP agent execution timed out after {execution_time:.2f}s")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error="ACP agent execution timed out",
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"ACP agent execution failed: {e}")
            return RuntimeResult(
                status=RuntimeStatus.FAILED,
                error=f"ACP agent execution failed: {str(e)}",
                execution_time=execution_time
            )

    def get_execution_stats(self, agent_id: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
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
    
    # =============================================================================
    # PERSISTENT AGENT METHODS
    # =============================================================================

    async def execute_initialization(self, execution_id: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute agent initialization."""
        # Use system database session for internal operations
        execution = self._get_execution_system(execution_id)
        if not execution:
            return {"status": "error", "message": "Execution not found"}
        
        # Use provided user_id or fall back to execution's user_id
        current_user_id = user_id or execution.user_id or 1
        
        # Start resource tracking for this execution
        await self.resource_manager.start_execution(execution_id, current_user_id)
        
        # Update status to running
        self.update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        try:
            # Get agent details
            agent = self.db.query(Agent).filter(Agent.id == execution.agent_id).first()
            if not agent:
                raise Exception("Agent not found")
            
            # Check if agent has a Docker deployment for this hiring
            deployment = self._get_active_deployment_for_hiring(execution.hiring_id)
            if deployment:
                # Use Docker-based persistent agent
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
                result = deployment_service.initialize_persistent_agent(deployment.deployment_id, execution.input_data or {})
            else:
                # Persistent agents require Docker deployment - no in-process fallback
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": f"Persistent agent {agent.id} requires Docker deployment for initialization. No deployment found for hiring {execution.hiring_id}."
                }
            
            # End resource tracking and get usage summary
            usage_summary = await self.resource_manager.end_execution(execution_id, "completed")
            
            if result.get('status') == 'success':
                self.update_execution_status(execution_id, ExecutionStatus.COMPLETED, result.get('result', {}))
                return {
                    "status": "success",
                    "execution_id": execution_id,
                    "result": result.get('result', {}),
                    "message": result.get('message', 'Initialization completed successfully'),
                    "usage_summary": usage_summary
                }
            else:
                # Don't call end_execution again - it was already called above for success case
                error_msg = result.get('error', 'Initialization failed')
                self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg)
                return {
                    "status": "error",
                    "execution_id": execution_id,
                    "error": error_msg
                }
        
        except Exception as e:
            # End resource tracking on error
            await self.resource_manager.end_execution(execution_id, "failed")
            error_msg = f"Initialization failed: {str(e)}"
            self.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=error_msg)
            return {
                "status": "error",
                "execution_id": execution_id,
                "error": error_msg
            }

    
    async def cleanup_persistent_agent(self, agent_id: str) -> Dict[str, Any]:
        """Clean up a persistent agent."""
        try:
            # Get agent details
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                return {"error": "Agent not found"}
            
            # Check if agent has a Docker deployment
            deployment = self._get_active_deployment_for_agent(agent_id)
            if deployment:
                # Use Docker-based persistent agent
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)

                # Track execution time
                import time
                start_time = time.time()

                # The deployment service now returns immediately for cleanup
                result = deployment_service.cleanup_persistent_agent(deployment.deployment_id)
                
                execution_time = time.time() - start_time
                logger.info(f"⏱️ Persistent agent cleanup started in {execution_time:.2f}s")

                # Add execution time to result
                if isinstance(result, dict):
                    result['execution_time'] = execution_time
                
                return result
            else:
                # Persistent agents require Docker deployment - no in-process fallback
                return {"error": f"Persistent agent {agent_id} requires Docker deployment for cleanup. No deployment found."}
                
        except Exception as e:
            logger.error(f"Error cleaning up persistent agent {agent_id}: {e}")
            return {"error": str(e)}
    
    def get_persistent_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get the status of a persistent agent."""
        try:
            status = self.persistent_runtime.get_agent_status(agent_id)
            if status:
                return {"status": "success", "data": status}
            else:
                return {"status": "not_found", "message": f"Agent {agent_id} not found"}
        except Exception as e:
            logger.error(f"Error getting persistent agent status {agent_id}: {e}")
            return {"error": str(e)}
    
    def list_persistent_agents(self) -> Dict[str, Any]:
        """List all persistent agents."""
        try:
            agents = self.persistent_runtime.list_agents()
            return {"status": "success", "data": agents}
        except Exception as e:
            logger.error(f"Error listing persistent agents: {e}")
            return {"error": str(e)}
    
    def _get_agent_config(self, agent: Agent) -> Dict[str, Any]:
        """Get agent configuration from agent files."""
        try:
            logger.info(f"Getting agent config for agent {agent.id}")
            agent_files = self._get_agent_files(agent.id)
            logger.info(f"Found {len(agent_files) if agent_files else 0} agent files")
            
            if not agent_files:
                logger.warning(f"No agent files found for agent {agent.id}")
                return {}
                
            for file_data in agent_files:
                logger.info(f"Checking file: {file_data.get('file_path')}")
                if file_data.get('file_path') == 'config.json':
                    logger.info(f"Found config.json, content length: {len(file_data.get('file_content', ''))}")
                    return json.loads(file_data['file_content'])
                    
            logger.warning(f"No config.json found in agent files for agent {agent.id}")
            return {}
        except Exception as e:
            logger.error(f"Error getting agent config for agent {agent.id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _get_active_deployment_for_agent(self, agent_id: str):
        """Get active deployment for an agent."""
        try:
            from ..models.deployment import AgentDeployment, DeploymentStatus
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.agent_id == agent_id,
                AgentDeployment.status == DeploymentStatus.RUNNING.value
            ).first()
            return deployment
        except Exception as e:
            logger.error(f"Error getting deployment for agent {agent_id}: {e}")
            return None
    
    def _get_active_deployment_for_hiring(self, hiring_id: int):
        """Get active deployment for a hiring."""
        try:
            from ..models.deployment import AgentDeployment, DeploymentStatus
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring_id,
                AgentDeployment.status == DeploymentStatus.RUNNING.value
            ).first()
            return deployment
        except Exception as e:
            logger.error(f"Error getting deployment for hiring {hiring_id}: {e}")
            return None

    async def execute_cleanup(self, execution_id: str, user_id: int) -> Dict[str, Any]:
        """Execute a cleanup operation for a hiring."""
        try:
            logger.info(f"Starting cleanup execution: {execution_id}")
            
            # Get the execution record
            execution = self.system_db.query(Execution).filter(Execution.execution_id == execution_id).first()
            if not execution:
                logger.error(f"Cleanup execution not found: {execution_id}")
                return {"status": "error", "error": "Execution not found"}
            
            # Update execution status to running
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.utcnow()
            self.system_db.commit()
            
            # Get the hiring to find the agent
            hiring = self.system_db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
            if not hiring:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.error_message = "Hiring not found"
                self.system_db.commit()
                return {"status": "error", "error": "Hiring not found"}
            
            # Get the agent
            agent = self.system_db.query(Agent).filter(Agent.id == hiring.agent_id).first()
            if not agent:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.error_message = "Agent not found"
                self.system_db.commit()
                return {"status": "error", "error": "Agent not found"}
            
            # Perform cleanup based on agent type
            if agent.agent_type == "persistent":
                # Clean up persistent agent
                logger.info(f"Cleaning up persistent agent: {agent.id}")
                cleanup_result = await self.cleanup_persistent_agent(str(agent.id))
            else:
                # For function agents, just mark the hiring as completed
                logger.info(f"Cleaning up function agent: {agent.id}")
                cleanup_result = {"status": "success", "message": "Function agent cleanup completed"}
            
            logger.info(f"Cleanup result: {cleanup_result}")
            
            # Update execution status
            if cleanup_result.get("status") == "success":
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
                execution.output_data = cleanup_result
            else:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = datetime.utcnow()
                execution.error_message = cleanup_result.get("error", "Cleanup failed")
            
            self.system_db.commit()
            
            # Update hiring status to cancelled (cleanup completed)
            hiring.status = "cancelled"
            self.system_db.commit()
            
            logger.info(f"Cleanup execution completed successfully: {execution_id}")
            return cleanup_result
            
        except Exception as e:
            logger.error(f"Error executing cleanup for execution {execution_id}: {e}")
            
            # Update execution status to failed
            try:
                execution = self.system_db.query(Execution).filter(Execution.execution_id == execution_id).first()
                if execution:
                    execution.status = ExecutionStatus.FAILED
                    execution.completed_at = datetime.utcnow()
                    execution.error_message = str(e)
                    self.system_db.commit()
            except:
                pass
            
            return {"status": "error", "error": str(e)} 