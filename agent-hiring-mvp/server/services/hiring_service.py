"""Hiring service for managing agent hiring workflow."""

import logging
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
        """Setup deployment for any agent type in background thread."""
        def deploy_in_background():
            try:
                # Create a new database session for the background thread
                from ..database.config import get_engine
                from sqlalchemy.orm import sessionmaker
                
                engine = get_engine()
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                db = SessionLocal()
                
                try:
                    # Import here to avoid circular imports
                    if agent.agent_type == AgentType.FUNCTION.value:
                        from .function_deployment_service import FunctionDeploymentService
                        deployment_service = FunctionDeploymentService(db)
                    else:
                        from .deployment_service import DeploymentService
                        deployment_service = DeploymentService(db)
                    
                    # Create deployment
                    if agent.agent_type == AgentType.FUNCTION.value:
                        deployment_result = deployment_service.create_function_deployment(hiring.id)
                    else:
                        deployment_result = deployment_service.create_deployment(hiring.id)
                    
                    if "error" in deployment_result:
                        logger.error(f"Failed to create deployment for hiring {hiring.id}: {deployment_result['error']}")
                        return
                    
                    deployment_id = deployment_result["deployment_id"]
                    logger.info(f"Created deployment {deployment_id} for hiring {hiring.id}")
                    
                    # Build and deploy the container
                    if agent.agent_type == AgentType.FUNCTION.value:
                        deploy_result = deployment_service.build_and_deploy_function(deployment_id)
                    else:
                        deploy_result = deployment_service.build_and_deploy(deployment_id)
                    
                    if "error" in deploy_result:
                        logger.error(f"Failed to deploy {deployment_id}: {deploy_result['error']}")
                        return
                    
                    logger.info(f"Successfully deployed {agent.agent_type} agent {agent.id} for hiring {hiring.id}")
                    
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Exception in agent deployment setup: {e}")
        
        # Start deployment in background thread
        deployment_thread = threading.Thread(target=deploy_in_background, daemon=True)
        deployment_thread.start()
        logger.info(f"Started {agent.agent_type} agent deployment in background for hiring {hiring.id}")
    
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
    
    def update_hiring_status(self, hiring_id: int, status: HiringStatus, 
                           notes: Optional[str] = None) -> Optional[Hiring]:
        """Update hiring status and handle agent-specific actions."""
        hiring = self.get_hiring(hiring_id)
        if not hiring:
            return None
        
        old_status = hiring.status
        
        # Check if hiring is already in the target status
        if old_status == status.value:
            # For cancellation, always attempt to clean up containers even if already cancelled
            if status == HiringStatus.CANCELLED:
                logger.info(f"Hiring {hiring_id} is already {status.value}, but attempting to clean up any remaining containers")
                # Attempt to clean up any remaining containers
                acp_cancellation_success = self._handle_acp_agent_cancellation(hiring, timeout=60)
                function_cancellation_success = self._handle_function_agent_cancellation(hiring, timeout=60)
                persistent_cancellation_success = self._handle_persistent_agent_cancellation(hiring, timeout=60)
                
                if not acp_cancellation_success or not function_cancellation_success or not persistent_cancellation_success:
                    logger.warning(f"Some resources may not have been fully terminated for hiring {hiring_id}")
                
                self.db.commit()
                self.db.refresh(hiring)
                return hiring
            else:
                # Return the hiring without making changes, but log the attempt
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
            # For function agents, also suspend the deployment
            self._handle_function_agent_suspension(hiring)
            # For persistent agents, also suspend the deployment
            self._handle_persistent_agent_suspension(hiring)
        elif status == HiringStatus.CANCELLED:
            hiring.last_executed_at = datetime.now(timezone.utc)
            # For ACP agents, stop and remove the deployment
            acp_cancellation_success = self._handle_acp_agent_cancellation(hiring, timeout=60)
            # For function agents, stop and remove the deployment
            function_cancellation_success = self._handle_function_agent_cancellation(hiring, timeout=60)
            # For persistent agents, stop and remove the deployment
            persistent_cancellation_success = self._handle_persistent_agent_cancellation(hiring, timeout=60)
            
            if not acp_cancellation_success or not function_cancellation_success or not persistent_cancellation_success:
                logger.warning(f"Some resources may not have been fully terminated for hiring {hiring_id}")
        
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
    
    def _handle_acp_agent_cancellation(self, hiring: Hiring, timeout: int = 60):
        """Handle ACP agent cancellation (stop and remove deployment)."""
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
                    logger.info(f"Starting cancellation process for deployment {deployment.deployment_id}")
                    
                    # Stop and remove the deployment with timeout
                    stop_result = deployment_service.stop_deployment(deployment.deployment_id, timeout=timeout)
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
            logger.error(f"Exception handling ACP agent cancellation: {e}")
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
    
    def _handle_function_agent_cancellation(self, hiring: Hiring, timeout: int = 60):
        """Handle function agent cancellation (stop and remove deployment)."""
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
                    logger.info(f"Starting function cancellation process for deployment {deployment.deployment_id}")
                    
                    # Stop and remove the deployment with timeout
                    stop_result = deployment_service.stop_function_deployment(deployment.deployment_id)
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
            logger.error(f"Exception handling function agent cancellation: {e}")
            return False
    
    def _handle_persistent_agent_cancellation(self, hiring: Hiring, timeout: int = 60):
        """Handle persistent agent cancellation (stop and remove deployment)."""
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
                    logger.info(f"Starting persistent agent cancellation process for deployment {deployment.deployment_id}")
                    
                    # First, try to cleanup the persistent agent (save state, etc.)
                    try:
                        cleanup_result = deployment_service.cleanup_persistent_agent(deployment.deployment_id)
                        if "error" in cleanup_result:
                            logger.warning(f"Failed to cleanup persistent agent {deployment.deployment_id}: {cleanup_result['error']}")
                        else:
                            logger.info(f"Successfully cleaned up persistent agent {deployment.deployment_id}")
                    except Exception as e:
                        logger.warning(f"Error during persistent agent cleanup: {e}")
                    
                    # Stop and remove the deployment with timeout
                    stop_result = deployment_service.stop_deployment(deployment.deployment_id, timeout=timeout)
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
            logger.error(f"Exception handling persistent agent cancellation: {e}")
            return False
    
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
    
    def activate_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Activate a hiring and return deployment info for ACP agents."""
        hiring = self.update_hiring_status(hiring_id, HiringStatus.ACTIVE, notes)
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
    
    def suspend_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Suspend a hiring."""
        return self.update_hiring_status(hiring_id, HiringStatus.SUSPENDED, notes)
    
    def cancel_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Cancel a hiring."""
        return self.update_hiring_status(hiring_id, HiringStatus.CANCELLED, notes)
    
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