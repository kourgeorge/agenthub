"""Hiring service for managing agent hiring workflow."""

import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.hiring import Hiring, HiringStatus
from ..models.agent import Agent, AgentType, AgentStatus
from ..models.user import User
from ..models.deployment import AgentDeployment

logger = logging.getLogger(__name__)


class HiringCreateRequest(BaseModel):
    """Request model for creating a hiring."""
    agent_id: str
    user_id: int
    requirements: Optional[Dict[str, Any]] = None
    budget: Optional[float] = None
    duration_hours: Optional[int] = None
    billing_cycle: Optional[str] = "per_use"  # per_use, monthly


class HiringService:
    """Service for managing agent hiring workflow."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_hiring(self, hiring_data: HiringCreateRequest) -> Hiring:
        """Create a new hiring record and handle agent-specific setup."""
        # Validate that the agent exists
        agent = self.db.query(Agent).filter(Agent.id == hiring_data.agent_id).first()
        if not agent:
            raise ValueError(f"Agent with ID {hiring_data.agent_id} does not exist")
        
        # Check if agent is approved OR if the user is hiring their own agent
        if agent.status != AgentStatus.APPROVED.value and agent.owner_id != hiring_data.user_id:
            raise ValueError(f"Agent {agent.id} is not approved (status: {agent.status}) and you don't own it")
        
        hiring = Hiring(
            agent_id=hiring_data.agent_id,
            user_id=hiring_data.user_id,
            status=HiringStatus.ACTIVE.value,
            config=hiring_data.requirements or {},
            billing_cycle=hiring_data.billing_cycle,
            hired_at=datetime.now(timezone.utc),
        )
        
        self.db.add(hiring)
        self.db.commit()
        self.db.refresh(hiring)
        
        logger.info(f"Created hiring: {hiring.id} for agent {hiring_data.agent_id}")
        
        # Handle agent deployment for all agent types
        if agent.agent_type in ["function", "persistent", "acp"]:
            # For all agent types, start deployment in background thread
            self._setup_agent_deployment_async(hiring, agent)
        else:
            logger.warning(f"Unknown agent type {agent.agent_type} for agent {agent.id}")
        
        return hiring
    
    def _setup_agent_deployment_async(self, hiring: Hiring, agent: Agent):
        """Setup deployment for any agent type."""
        try:
            # Import here to avoid circular imports
            if agent.agent_type == AgentType.FUNCTION.value:
                from .function_deployment_service import FunctionDeploymentService
                deployment_service = FunctionDeploymentService(self.db)
            else:
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
            
            # Create deployment record only
            if agent.agent_type == AgentType.FUNCTION.value:
                deployment_result = deployment_service.create_function_deployment(hiring.id)
            else:
                deployment_result = deployment_service.create_deployment(hiring.id)
            
            if "error" in deployment_result:
                logger.error(f"Failed to create deployment for hiring {hiring.id}: {deployment_result['error']}")
                return
            
            deployment_id = deployment_result["deployment_id"]
            logger.info(f"Created deployment {deployment_id} for hiring {hiring.id}")
            
            # Start build process in background thread (non-blocking)
            import threading
            if agent.agent_type == AgentType.FUNCTION.value:
                thread = threading.Thread(
                    target=self._run_function_deployment,
                    args=(deployment_id,),
                    daemon=True
                )
            else:
                thread = threading.Thread(
                    target=self._run_acp_deployment,
                    args=(deployment_id,),
                    daemon=True
                )
            
            thread.start()
            logger.info(f"Started build and deploy thread for {agent.agent_type} agent {deployment_id}")
            
        except Exception as e:
            logger.error(f"Exception in agent deployment setup: {e}")
    
    def _run_function_deployment(self, deployment_id):
        """Run function deployment in background thread."""
        try:
            # Create new database session for this thread
            from ..database.config import get_session_dependency
            db = next(get_session_dependency())
            
            # Create new deployment service with fresh session
            from .function_deployment_service import FunctionDeploymentService
            deployment_service = FunctionDeploymentService(db)
            
            import asyncio
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(deployment_service.build_and_deploy_function(deployment_id))
            
        except Exception as e:
            logger.error(f"Background function deployment failed for {deployment_id}: {e}")
    
    def _run_acp_deployment(self, deployment_id):
        """Run ACP deployment in background thread."""
        try:
            # Create new database session for this thread
            from ..database.config import get_session_dependency
            db = next(get_session_dependency())
            
            # Create new deployment service with fresh session
            from .deployment_service import DeploymentService
            deployment_service = DeploymentService(db)
            
            import asyncio
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(deployment_service.build_and_deploy(deployment_id))
            
        except Exception as e:
            logger.error(f"Background ACP deployment failed for {deployment_id}: {e}")
    
    def _setup_acp_agent_deployment(self, hiring: Hiring, agent: Agent):
        """Setup deployment for ACP server agent (synchronous version - kept for compatibility)."""
        try:
            # Import here to avoid circular imports
            from .deployment_service import DeploymentService
            
            deployment_service = DeploymentService(self.db)
            
            # Create deployment
            deployment_result = deployment_service.create_deployment(hiring.id)
            if "error" in deployment_result:
                logger.error(f"Failed to create deployment for hiring {hiring.id}: {deployment_result['error']}")
                return
            
            deployment_id = deployment_result["deployment_id"]
            logger.info(f"Created deployment {deployment_id} for hiring {hiring.id}")
            
            # Build and deploy the container
            deploy_result = deployment_service.build_and_deploy(deployment_id)
            if "error" in deploy_result:
                logger.error(f"Failed to deploy {deployment_id}: {deploy_result['error']}")
                return
            
            logger.info(f"Successfully deployed ACP agent {agent.id} for hiring {hiring.id}")
            
        except Exception as e:
            logger.error(f"Exception in ACP agent deployment setup: {e}")
    
    def get_hiring(self, hiring_id: int) -> Optional[Hiring]:
        """Get a hiring by ID."""
        return self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
    
    async def update_hiring_status(self, hiring_id: int, status: HiringStatus,
                                  timeout: int = 60) -> Optional[Hiring]:
        """Update hiring status and handle associated deployment changes."""
        hiring = self.get_hiring(hiring_id)
        if not hiring:
            return None
        
        old_status = hiring.status
        logger.info(f"Updating hiring {hiring_id} status from {old_status} to {status.value}")
        
        # If the hiring is already in the target status, return without changes
        if hiring.status == status.value:
            logger.info(f"Hiring {hiring_id} is already {status.value}")
            return hiring
        
        hiring.status = status.value
        
        if status == HiringStatus.ACTIVE:
            hiring.hired_at = datetime.now(timezone.utc)
            # If reactivating a suspended agent, restart deployment
            if old_status == HiringStatus.SUSPENDED.value:
                self._handle_acp_agent_activation(hiring)
                # Also handle function agent activation
                self._handle_function_agent_activation(hiring)
                # Also handle persistent agent activation
                self._handle_persistent_agent_activation(hiring)
        elif status == HiringStatus.SUSPENDED:
            hiring.last_executed_at = datetime.now(timezone.utc)
            # For ACP agents, suspend the deployment (keep container but stop processing)
            self._handle_acp_agent_suspension(hiring)
            # Also handle function agent suspension
            self._handle_function_agent_suspension(hiring)
            # Also handle persistent agent suspension
            self._handle_persistent_agent_suspension(hiring)
        elif status == HiringStatus.CANCELLED:
            hiring.last_executed_at = datetime.now(timezone.utc)
            # For cancellation, we now use the async background process
            # The actual cancellation work is handled by perform_cancellation_work
            # This method just updates the status and returns immediately
            logger.info(f"Hiring {hiring_id} marked for cancellation - background process will handle cleanup")
        
        self.db.commit()
        self.db.refresh(hiring)
        
        logger.info(f"Updated hiring {hiring_id} status to {status.value}")
        return hiring
    
    def _handle_acp_agent_activation(self, hiring: Hiring) -> Optional[Dict[str, Any]]:
        """Handle ACP agent activation (resume deployment)."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == AgentType.ACP_SERVER.value:
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    # Resume the deployment
                    resume_result = deployment_service.resume_deployment(deployment.deployment_id)
                    if "error" in resume_result:
                        logger.error(f"Failed to resume deployment {deployment.deployment_id}: {resume_result['error']}")
                        return None
                    else:
                        logger.info(f"Successfully resumed deployment {deployment.deployment_id}")
                        
                        # Return deployment information for CLI display
                        return {
                            "deployment_id": deployment.deployment_id,
                            "status": deployment.status,
                            "proxy_endpoint": deployment.proxy_endpoint,
                            "external_port": deployment.external_port,
                            "container_id": deployment.container_id,
                            "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                        }
            return None
        except Exception as e:
            logger.error(f"Exception handling ACP agent activation: {e}")
            return None
    
    def _handle_acp_agent_suspension(self, hiring: Hiring):
        """Handle ACP agent suspension (suspend deployment)."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == AgentType.ACP_SERVER.value:
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    # Suspend the deployment (stop container but keep it)
                    suspend_result = deployment_service.suspend_deployment(deployment.deployment_id)
                    if "error" in suspend_result:
                        logger.error(f"Failed to suspend deployment {deployment.deployment_id}: {suspend_result['error']}")
                    else:
                        logger.info(f"Successfully suspended deployment {deployment.deployment_id}")
        except Exception as e:
            logger.error(f"Exception handling ACP agent suspension: {e}")
    

    
    async def _handle_acp_agent_cancellation_async(self, hiring: Hiring, timeout: int = 60):
        """Async version of ACP agent cancellation - truly non-blocking."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == AgentType.ACP_SERVER.value:
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    logger.info(f"Starting async cancellation process for deployment {deployment.deployment_id}")
                    
                    # Run the blocking operation in a thread pool to make it non-blocking
                    loop = asyncio.get_event_loop()
                    stop_result = await loop.run_in_executor(
                        None, 
                        lambda: deployment_service.stop_deployment(deployment.deployment_id, timeout=timeout)
                    )
                    
                    if "error" in stop_result:
                        logger.error(f"Failed to stop deployment {deployment.deployment_id}: {stop_result['error']}")
                        return False
                    else:
                        logger.info(f"Successfully stopped deployment {deployment.deployment_id}")
                        
                    # Update deployment status to cancelled instead of deleting
                    deployment.status = "cancelled"
                    deployment.stopped_at = datetime.now(timezone.utc)
                    deployment.is_healthy = False
                    self.db.commit()
                    logger.info(f"Updated deployment {deployment.deployment_id} status to cancelled for hiring {hiring.id}")
                    return True
            return True  # No deployment to cancel
        except Exception as e:
            logger.error(f"Exception handling async ACP agent cancellation: {e}")
            return False
    
    def _handle_function_agent_activation(self, hiring: Hiring):
        """Handle function agent activation (resume deployment)."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == AgentType.FUNCTION.value:
                from .function_deployment_service import FunctionDeploymentService
                deployment_service = FunctionDeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    # Resume the deployment
                    resume_result = deployment_service.resume_function_deployment(deployment.deployment_id)
                    if "error" in resume_result:
                        logger.error(f"Failed to resume function deployment {deployment.deployment_id}: {resume_result['error']}")
                    else:
                        logger.info(f"Successfully resumed function deployment {deployment.deployment_id}")
        except Exception as e:
            logger.error(f"Exception handling function agent activation: {e}")

    def _handle_function_agent_suspension(self, hiring: Hiring):
        """Handle function agent suspension (suspend deployment)."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == AgentType.FUNCTION.value:
                from .function_deployment_service import FunctionDeploymentService
                deployment_service = FunctionDeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    # Suspend the deployment (stop container but keep it)
                    suspend_result = deployment_service.suspend_function_deployment(deployment.deployment_id)
                    if "error" in suspend_result:
                        logger.error(f"Failed to suspend function deployment {deployment.deployment_id}: {suspend_result['error']}")
                    else:
                        logger.info(f"Successfully suspended function deployment {deployment.deployment_id}")
        except Exception as e:
            logger.error(f"Exception handling function agent suspension: {e}")
    

    
    async def _handle_function_agent_cancellation_async(self, hiring: Hiring, timeout: int = 60):
        """Async version of function agent cancellation - truly non-blocking."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == AgentType.FUNCTION.value:
                from .function_deployment_service import FunctionDeploymentService
                deployment_service = FunctionDeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    logger.info(f"Starting async function cancellation process for deployment {deployment.deployment_id}")
                    
                    # Run the blocking operation in a thread pool to make it non-blocking
                    loop = asyncio.get_event_loop()
                    stop_result = await loop.run_in_executor(
                        None, 
                        lambda: deployment_service.stop_function_deployment(deployment.deployment_id)
                    )
                    
                    if "error" in stop_result:
                        logger.error(f"Failed to stop function deployment {deployment.deployment_id}: {stop_result['error']}")
                        return False
                    else:
                        logger.info(f"Successfully stopped function deployment {deployment.deployment_id}")
                        
                    # Update deployment status to cancelled instead of deleting
                    deployment.status = "cancelled"
                    deployment.stopped_at = datetime.now(timezone.utc)
                    deployment.is_healthy = False
                    self.db.commit()
                    logger.info(f"Updated function deployment {deployment.deployment_id} status to cancelled for hiring {hiring.id}")
                    return True
            return True  # No deployment to cancel
        except Exception as e:
            logger.error(f"Exception handling async function agent cancellation: {e}")
            return False
    

    
    async def _handle_persistent_agent_cancellation_async(self, hiring: Hiring, timeout: int = 60):
        """Async version of persistent agent cancellation - truly non-blocking."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == "persistent":
                from .deployment_service import DeploymentService
                from ..models.deployment import AgentDeployment
                
                deployment_service = DeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    logger.info(f"Starting async persistent agent cancellation process for deployment {deployment.deployment_id}")
                    
                    # Run cleanup and stop operations in thread pool to make them non-blocking
                    loop = asyncio.get_event_loop()
                    
                    # Run cleanup in thread pool
                    cleanup_result = await loop.run_in_executor(
                        None,
                        lambda: self._cleanup_persistent_agent_sync(deployment_service, deployment.deployment_id)
                    )
                    
                    # Run stop deployment in thread pool
                    stop_result = await loop.run_in_executor(
                        None,
                        lambda: deployment_service.stop_deployment(deployment.deployment_id, timeout=timeout)
                    )
                    
                    if "error" in stop_result:
                        logger.error(f"Failed to stop persistent deployment {deployment.deployment_id}: {stop_result['error']}")
                        return False
                    else:
                        logger.info(f"Successfully stopped persistent deployment {deployment.deployment_id}")
                        
                    # Update deployment status to cancelled instead of deleting
                    deployment.status = "cancelled"
                    deployment.stopped_at = datetime.now(timezone.utc)
                    deployment.is_healthy = False
                    self.db.commit()
                    logger.info(f"Updated persistent deployment {deployment.deployment_id} status to cancelled for hiring {hiring.id}")
                    return True
            return True  # No deployment to cancel
        except Exception as e:
            logger.error(f"Exception handling async persistent agent cancellation: {e}")
            return False
    
    def _cleanup_persistent_agent_sync(self, deployment_service, deployment_id: str):
        """Synchronous wrapper for persistent agent cleanup."""
        try:
            # Call the synchronous cleanup method directly
            cleanup_result = deployment_service.cleanup_persistent_agent(deployment_id)
            if "error" in cleanup_result:
                logger.warning(f"Failed to cleanup persistent agent {deployment_id}: {cleanup_result['error']}")
            else:
                logger.info(f"Successfully cleaned up persistent agent {deployment_id}")
        except Exception as e:
            logger.warning(f"Error during persistent agent cleanup: {e}")
    
    def _handle_persistent_agent_activation(self, hiring: Hiring) -> Optional[Dict[str, Any]]:
        """Handle persistent agent activation (resume deployment)."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == "persistent":
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    # Resume the deployment
                    resume_result = deployment_service.resume_deployment(deployment.deployment_id)
                    if "error" in resume_result:
                        logger.error(f"Failed to resume persistent deployment {deployment.deployment_id}: {resume_result['error']}")
                        return None
                    else:
                        logger.info(f"Successfully resumed persistent deployment {deployment.deployment_id}")
                        
                        # Return deployment information for CLI display
                        return {
                            "deployment_id": deployment.deployment_id,
                            "status": deployment.status,
                            "container_id": deployment.container_id,
                            "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                        }
            return None
        except Exception as e:
            logger.error(f"Exception handling persistent agent activation: {e}")
            return None
    
    def _handle_persistent_agent_suspension(self, hiring: Hiring):
        """Handle persistent agent suspension (suspend deployment)."""
        try:
            agent = hiring.agent
            if agent and agent.agent_type == "persistent":
                from .deployment_service import DeploymentService
                deployment_service = DeploymentService(self.db)
                
                # Find existing deployment
                deployment = self.db.query(AgentDeployment).filter(
                    AgentDeployment.hiring_id == hiring.id
                ).first()
                
                if deployment:
                    # Suspend the deployment (stop container but keep it)
                    suspend_result = deployment_service.suspend_deployment(deployment.deployment_id)
                    if "error" in suspend_result:
                        logger.error(f"Failed to suspend persistent deployment {deployment.deployment_id}: {suspend_result['error']}")
                    else:
                        logger.info(f"Successfully suspended persistent deployment {deployment.deployment_id}")
        except Exception as e:
            logger.error(f"Exception handling persistent agent suspension: {e}")
    
    def get_user_hirings(self, user_id: int, status: Optional[HiringStatus] = None) -> List[Hiring]:
        """Get hirings for a user."""
        query = self.db.query(Hiring).filter(Hiring.user_id == user_id)
        
        if status:
            query = query.filter(Hiring.status == status.value)
        
        return query.order_by(Hiring.created_at.desc()).all()
    
    def get_agent_hirings(self, agent_id: str, status: Optional[HiringStatus] = None) -> List[Hiring]:
        """Get hirings for an agent."""
        query = self.db.query(Hiring).filter(Hiring.agent_id == agent_id)
        
        if status:
            query = query.filter(Hiring.status == status.value)
        
        return query.order_by(Hiring.created_at.desc()).all()
    
    async def activate_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Activate a hiring and return deployment info for ACP agents."""
        hiring = await self.update_hiring_status(hiring_id, HiringStatus.ACTIVE, notes)
        if not hiring:
            return None
        
        # Get deployment information for ACP agents
        deployment_info = None
        if hiring.agent.agent_type == AgentType.ACP_SERVER.value:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring_id
            ).first()
            
            if deployment:
                deployment_info = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "container_id": deployment.container_id,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        return {
            "hiring_id": hiring.id,
            "agent_id": hiring.agent_id,
            "agent_name": hiring.agent.name,
            "agent_type": hiring.agent.agent_type,
            "status": hiring.status,
            "deployment": deployment_info
        }
    
    async def suspend_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Suspend a hiring."""
        return await self.update_hiring_status(hiring_id, HiringStatus.SUSPENDED, notes)
    
    async def cancel_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Cancel a hiring."""
        return await self.update_hiring_status(hiring_id, HiringStatus.CANCELLED, notes)
    
    async def perform_cancellation_work(self, hiring_id: int, notes: Optional[str], timeout: int):
        """Background method for actual cancellation work - truly non-blocking."""
        try:
            # Get the hiring with a fresh database session
            from ..database.config import get_session_dependency
            db = next(get_session_dependency())
            hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
            
            if not hiring:
                logger.error(f"Hiring {hiring_id} not found during background cancellation")
                return
            
            # Create a task that runs the blocking operations in a separate thread
            # This ensures the main event loop is never blocked
            loop = asyncio.get_event_loop()
            
            # Run the entire cancellation process in a thread pool
            # This is the key - we move ALL blocking operations to a separate thread
            result = await loop.run_in_executor(
                None,  # Use default thread pool
                self._perform_cancellation_sync,  # Run the sync version in thread
                hiring_id, notes, timeout
            )
            
            logger.info(f"Background cancellation completed for hiring {hiring_id}: {result}")
            
        except Exception as e:
            logger.error(f"Exception during background cancellation for hiring {hiring_id}: {e}")
            # Try to update status to failed
            try:
                from ..database.config import get_session_dependency
                db = next(get_session_dependency())
                hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
                if hiring:
                    hiring.status = HiringStatus.CANCELLATION_FAILED.value
                    hiring.last_executed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update hiring status to failed: {update_error}")
    
    def _perform_cancellation_sync(self, hiring_id: int, notes: Optional[str], timeout: int):
        """Synchronous method that runs in a separate thread - truly non-blocking for main process."""
        try:
            # Get the hiring with a fresh database session for this thread
            from ..database.config import get_session_dependency
            db = next(get_session_dependency())
            hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
            
            if not hiring:
                logger.error(f"Hiring {hiring_id} not found during sync cancellation")
                return False
            
            logger.info(f"Starting sync cancellation for hiring {hiring_id} in thread")
            
            # Perform the actual cancellation operations using async methods
            

            
            # Run each cancellation operation with timeout in parallel using async methods
            # Since we're in a sync context, we need to create a new event loop for async operations
            import asyncio
            
            async def run_async_cancellations():
                """Run all cancellation operations asynchronously."""
                try:
                    # Run all operations concurrently with timeout
                    results = await asyncio.wait_for(
                        asyncio.gather(
                            self._handle_acp_agent_cancellation_async(hiring, timeout),
                            self._handle_function_agent_cancellation_async(hiring, timeout),
                            self._handle_persistent_agent_cancellation_async(hiring, timeout),
                            return_exceptions=True  # Don't fail if one operation fails
                        ),
                        timeout=timeout + 5  # Extra buffer
                    )
                    
                    # Extract results, handling any exceptions
                    acp_result = results[0] if not isinstance(results[0], Exception) else False
                    function_result = results[1] if not isinstance(results[1], Exception) else False
                    persistent_result = results[2] if not isinstance(results[2], Exception) else False
                    
                    return acp_result, function_result, persistent_result
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Async cancellation operations timed out for hiring {hiring_id}")
                    return False, False, False
                except Exception as e:
                    logger.error(f"Exception during async cancellation operations: {e}")
                    return False, False, False
            
            # Create new event loop for async operations
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                acp_cancellation_success, function_cancellation_success, persistent_cancellation_success = loop.run_until_complete(run_async_cancellations())
            finally:
                loop.close()
            
            # Update final status based on results
            if acp_cancellation_success and function_cancellation_success and persistent_cancellation_success:
                hiring.status = HiringStatus.CANCELLED.value
                logger.info(f"Successfully cancelled hiring {hiring_id}")
            else:
                hiring.status = HiringStatus.CANCELLATION_FAILED.value
                logger.warning(f"Some resources may not have been fully terminated for hiring {hiring_id}")
            
            hiring.last_executed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(hiring)
            
            return True
            
        except Exception as e:
            logger.error(f"Exception during sync cancellation for hiring {hiring_id}: {e}")
            # Try to update status to failed
            try:
                if hiring:
                    hiring.status = HiringStatus.CANCELLATION_FAILED.value
                    hiring.last_executed_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update hiring status to failed: {update_error}")
            return False
    
    def get_hiring_stats(self, user_id: Optional[int] = None, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get hiring statistics."""
        query = self.db.query(Hiring)
        
        if user_id:
            query = query.filter(Hiring.user_id == user_id)
        
        if agent_id:
            query = query.filter(Hiring.agent_id == agent_id)
        
        total_hirings = query.count()
        active_hirings = query.filter(Hiring.status == HiringStatus.ACTIVE.value).count()
        suspended_hirings = query.filter(Hiring.status == HiringStatus.SUSPENDED.value).count()
        cancelled_hirings = query.filter(Hiring.status == HiringStatus.CANCELLED.value).count()
        expired_hirings = query.filter(Hiring.status == HiringStatus.EXPIRED.value).count()
        
        return {
            "total_hirings": total_hirings,
            "active_hirings": active_hirings,
            "suspended_hirings": suspended_hirings,
            "cancelled_hirings": cancelled_hirings,
            "expired_hirings": expired_hirings,
            "active_rate": (active_hirings / total_hirings * 100) if total_hirings > 0 else 0,
        }
    
    def get_active_hirings(self) -> List[Hiring]:
        """Get all active hiring requests."""
        return (
            self.db.query(Hiring)
            .filter(Hiring.status == HiringStatus.ACTIVE.value)
            .order_by(Hiring.hired_at.asc())
            .all()
        )
    
    def get_hiring_with_details(self, hiring_id: int) -> Optional[Dict[str, Any]]:
        """Get hiring with agent and user details."""
        hiring = (
            self.db.query(Hiring)
            .join(Agent, Hiring.agent_id == Agent.id)
            .join(User, Hiring.user_id == User.id)
            .filter(Hiring.id == hiring_id)
            .first()
        )
        
        if not hiring:
            return None
        
        # Get deployment info for ACP agents
        deployment_info = None
        if hiring.agent.agent_type == AgentType.ACP_SERVER.value:
            deployment = self.db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring_id
            ).first()
            
            if deployment:
                deployment_info = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "container_id": deployment.container_id,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        return {
            "hiring_id": hiring.id,
            "agent_id": hiring.agent_id,
            "agent_name": hiring.agent.name,
            "agent_type": hiring.agent.agent_type,
            "agent_description": hiring.agent.description,
            "user_id": hiring.user_id,
            "username": hiring.user.username,
            "status": hiring.status,
            "billing_cycle": hiring.billing_cycle,
            "config": hiring.config,
            "hired_at": hiring.hired_at.isoformat(),
            "last_executed_at": hiring.last_executed_at.isoformat() if hiring.last_executed_at else None,
            "deployment": deployment_info
        } 