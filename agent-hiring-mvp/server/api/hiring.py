"""Hiring API endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.config import get_session_dependency
from ..services.hiring_service import HiringService, HiringCreateRequest
from ..models.hiring import Hiring, HiringStatus
from ..models.deployment import AgentDeployment
from ..middleware.auth import get_current_user, get_current_user_optional, get_current_user_required, require_same_user
from ..models.user import User

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hiring", tags=["hiring"])


@router.post("/", response_model=dict)
def create_hiring(
    hiring_data: HiringCreateRequest,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Create a new hiring request."""
    # Ensure the hiring is created for the authenticated user
    hiring_data.user_id = current_user.id
    
    hiring_service = HiringService(db)
    
    try:
        hiring = hiring_service.create_hiring(hiring_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Get agent information
    from ..models.agent import Agent
    agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
    
    response = {
        "id": hiring.id,
        "hiring_id": hiring.id,  # For consistency with CLI
        "agent_id": hiring.agent_id,
        "agent_name": agent.name if agent else f"Agent {hiring.agent_id}",
        "agent_type": agent.agent_type if agent else "unknown",
        "user_id": hiring.user_id,
        "status": hiring.status,
        "billing_cycle": hiring.billing_cycle,
        "hired_at": hiring.hired_at.isoformat(),
        "message": "Hiring created successfully"
    }
    
    # Add deployment status for ACP agents
    if agent and agent.agent_type == "acp_server":
        from ..models.deployment import AgentDeployment
        deployment = db.query(AgentDeployment).filter(
            AgentDeployment.hiring_id == hiring.id
        ).first()
        
        if deployment:
            response["deployment"] = {
                "deployment_id": deployment.deployment_id,
                "status": deployment.status,
                "proxy_endpoint": deployment.proxy_endpoint,
                "external_port": deployment.external_port,
                "container_id": deployment.container_id,
                "started_at": deployment.started_at.isoformat() if deployment.started_at else None
            }
    
    return response


@router.get("/user", response_model=List[dict])
def get_current_user_hirings(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Get all hirings for the current authenticated user."""
    hiring_service = HiringService(db)
    
    if status:
        try:
            hiring_status = HiringStatus(status)
            hirings = hiring_service.get_user_hirings(current_user.id, hiring_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    else:
        hirings = hiring_service.get_user_hirings(current_user.id)
    
    result = []
    for hiring in hirings:
        # Dynamically calculate execution count instead of using potentially outdated field
        from ..models.execution import Execution
        execution_count = db.query(Execution).filter(
            Execution.hiring_id == hiring.id
        ).count()
        
        hiring_data = {
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "status": hiring.status,
            "billing_cycle": hiring.billing_cycle,
            "hired_at": hiring.hired_at.isoformat(),
            "created_at": hiring.hired_at.isoformat(),  # Alias for frontend compatibility
            "total_executions": execution_count,  # Use dynamic count
            "total_cost": 0.0,  # Placeholder for future billing integration
        }
        
        # Add agent information
        if hiring.agent:
            hiring_data.update({
                "agent_name": hiring.agent.name,
                "agent_type": hiring.agent.agent_type,
                "agent_description": hiring.agent.description,
            })
        
        # Add deployment information for ACP agents
        if hiring.agent and hiring.agent.agent_type == "acp_server":
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                hiring_data["deployment"] = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "container_id": deployment.container_id,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        # Add deployment information for function agents
        elif hiring.agent and hiring.agent.agent_type == "function":
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                hiring_data["deployment"] = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "container_id": deployment.container_id,
                    "container_name": deployment.container_name,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        result.append(hiring_data)
    
    return result


@router.get("/user/{user_id}", response_model=List[dict])
def get_user_hirings(
    user_id: int,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Get all hirings for a user."""
    # Ensure the user can only access their own hirings
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only view your own hirings"
        )
    
    hiring_service = HiringService(db)
    
    if status:
        try:
            hiring_status = HiringStatus(status)
            hirings = hiring_service.get_user_hirings(user_id, hiring_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    else:
        hirings = hiring_service.get_user_hirings(user_id)
    
    result = []
    for hiring in hirings:
        # Dynamically calculate execution count for each hiring
        from ..models.execution import Execution
        execution_count = db.query(Execution).filter(
            Execution.hiring_id == hiring.id
        ).count()
        
        result.append({
            "id": hiring.id,
            "user_id": hiring.user_id,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": execution_count,  # Use dynamic count
        })
    
    return result


@router.get("/{hiring_id}", response_model=dict)
def get_hiring(
    hiring_id: int, 
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Get a hiring by ID."""
    hiring_service = HiringService(db)
    hiring = hiring_service.get_hiring(hiring_id)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure the user can only access their own hirings
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only view your own hirings"
        )
    
    # Dynamically calculate execution count instead of removed field
    from ..models.execution import Execution
    execution_count = db.query(Execution).filter(
        Execution.hiring_id == hiring.id
    ).count()
    
    response = {
        "id": hiring.id,
        "agent_id": hiring.agent_id,
        "user_id": hiring.user_id,
        "status": hiring.status,
        "hired_at": hiring.hired_at.isoformat(),
        "expires_at": hiring.expires_at.isoformat() if hiring.expires_at else None,
        "config": hiring.config,
        "state": hiring.state,
        "total_executions": execution_count,  # Use dynamic count
        "last_executed_at": hiring.last_executed_at.isoformat() if hiring.last_executed_at else None,
    }
    
    # Add agent information including agent_type
    if hiring.agent:
        response.update({
            "agent_name": hiring.agent.name,
            "agent_type": hiring.agent.agent_type,
            "agent_description": hiring.agent.description,
        })
    
    # Fetch deployment information
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring.id
    ).first()
    
    # Add deployment information if available
    if deployment:
        response["deployment"] = {
            "deployment_id": deployment.deployment_id,
            "status": deployment.status,
            "container_id": deployment.container_id,
            "container_name": deployment.container_name,
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None
        }
        
        # Add ACP-specific fields
        if deployment.proxy_endpoint:
            response["deployment"]["proxy_endpoint"] = deployment.proxy_endpoint
        if deployment.external_port:
            response["deployment"]["external_port"] = deployment.external_port
    
    return response


@router.get("/agent/{agent_id}", response_model=List[dict])
def get_agent_hirings(
    agent_id: str,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Get all hirings for an agent that belong to the current user."""
    hiring_service = HiringService(db)
    
    if status:
        try:
            hiring_status = HiringStatus(status)
            hirings = hiring_service.get_agent_hirings(agent_id, hiring_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    else:
        hirings = hiring_service.get_agent_hirings(agent_id)
    
    # Filter hirings to only show those belonging to the current user
    user_hirings = [hiring for hiring in hirings if hiring.user_id == current_user.id]
    
    result = []
    for hiring in user_hirings:
        # Dynamically calculate execution count for each hiring
        from ..models.execution import Execution
        execution_count = db.query(Execution).filter(
            Execution.hiring_id == hiring.id
        ).count()
        
        result.append({
            "id": hiring.id,
            "user_id": hiring.user_id,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": execution_count,  # Use dynamic count
        })
    
    return result


@router.put("/{hiring_id}/activate")
async def activate_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Activate a suspended hiring."""
    hiring_service = HiringService(db)
    
    try:
        hiring = hiring_service.get_hiring(hiring_id)
        if not hiring:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hiring not found"
            )
        
        # Ensure the user can only activate their own hirings
        if hiring.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only activate your own hirings"
            )
        
        # Check if hiring is already active
        if hiring.status == HiringStatus.ACTIVE:
            return {
                "message": "Hiring is already active",
                "hiring_id": hiring_id,
                "status": hiring.status.value,
                "already_active": True
            }
        
        # Check if hiring is suspended (can only activate suspended hirings)
        if hiring.status != HiringStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot activate hiring with status: {hiring.status.value}. Only suspended hirings can be activated."
            )
        
        # Activate the hiring
        updated_hiring = hiring_service.activate_hiring(hiring_id, notes)
        
        # Get agent information
        from ..models.agent import Agent
        agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
        
        response = {
            "message": "Hiring activated successfully",
            "hiring_id": hiring_id,
            "status": updated_hiring.status.value,
            "activated_at": updated_hiring.activated_at.isoformat() if updated_hiring.activated_at else None,
            "agent_id": hiring.agent_id,
            "agent_name": agent.name if agent else f"Agent {hiring.agent_id}",
            "agent_type": agent.agent_type if agent else "unknown",
            "already_active": False
        }
        
        # Add deployment information for ACP agents
        if agent and agent.agent_type == "acp_server":
            from ..models.deployment import AgentDeployment
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                response["deployment"] = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "container_id": deployment.container_id,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating hiring {hiring_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate hiring: {str(e)}"
        )


@router.put("/{hiring_id}/suspend")
async def suspend_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Suspend an active hiring."""
    hiring_service = HiringService(db)
    
    try:
        hiring = hiring_service.get_hiring(hiring_id)
        if not hiring:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hiring not found"
            )
        
        # Ensure the user can only suspend their own hirings
        if hiring.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only suspend your own hirings"
            )
        
        # Check if hiring is already suspended
        if hiring.status == HiringStatus.SUSPENDED:
            return {
                "message": "Hiring is already suspended",
                "hiring_id": hiring_id,
                "status": hiring.status.value,
                "already_suspended": True
            }
        
        # Check if hiring is active (can only suspend active hirings)
        if hiring.status != HiringStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot suspend hiring with status: {hiring.status.value}. Only active hirings can be suspended."
            )
        
        # Suspend the hiring
        updated_hiring = hiring_service.suspend_hiring(hiring_id, notes)
        
        # Get agent information
        from ..models.agent import Agent
        agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
        
        response = {
            "message": "Hiring suspended successfully",
            "hiring_id": hiring_id,
            "status": updated_hiring.status.value,
            "suspended_at": updated_hiring.suspended_at.isoformat() if updated_hiring.suspended_at else None,
            "agent_id": hiring.agent_id,
            "agent_name": agent.name if agent else f"Agent {hiring.agent_id}",
            "agent_type": agent.agent_type if agent else "unknown",
            "already_suspended": False
        }
        
        # Add deployment information for ACP agents
        if agent and agent.agent_type == "acp_server":
            from ..models.deployment import AgentDeployment
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                response["deployment"] = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "container_id": deployment.container_id,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suspending hiring {hiring_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suspend hiring: {str(e)}"
        )


@router.put("/{hiring_id}/cancel")
async def cancel_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    timeout: Optional[int] = 60,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Cancel a hiring and automatically stop associated deployments."""
    hiring_service = HiringService(db)
    
    try:
        hiring = hiring_service.get_hiring(hiring_id)
        if not hiring:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hiring not found"
            )
        
        # Ensure the user can only cancel their own hirings
        if hiring.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only cancel your own hirings"
            )
        
        # Check if hiring is already cancelled
        if hiring.status == HiringStatus.CANCELLED:
            return {
                "message": "Hiring is already cancelled",
                "hiring_id": hiring_id,
                "status": hiring.status.value,
                "already_cancelled": True
            }
        
        # Check if hiring can be cancelled (active or suspended hirings can be cancelled)
        if hiring.status not in [HiringStatus.ACTIVE, HiringStatus.SUSPENDED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel hiring with status: {hiring.status.value}. Only active or suspended hirings can be cancelled."
            )
        
        # Cancel the hiring
        updated_hiring = hiring_service.cancel_hiring(hiring_id, notes, timeout)
        
        # Get agent information
        from ..models.agent import Agent
        agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
        
        response = {
            "message": "Hiring cancelled successfully",
            "hiring_id": hiring_id,
            "status": updated_hiring.status.value,
            "cancelled_at": updated_hiring.cancelled_at.isoformat() if updated_hiring.cancelled_at else None,
            "agent_id": hiring.agent_id,
            "agent_name": agent.name if agent else f"Agent {hiring.agent_id}",
            "agent_type": agent.agent_type if agent else "unknown",
            "already_cancelled": False
        }
        
        # Add deployment information for ACP agents
        if agent and agent.agent_type == "acp_server":
            from ..models.deployment import AgentDeployment
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            if deployment:
                response["deployment"] = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "container_id": deployment.container_id,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None
                }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling hiring {hiring_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel hiring: {str(e)}"
        )


@router.get("/stats/user/{user_id}")
def get_user_hiring_stats(
    user_id: int, 
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_session_dependency)
):
    """Get hiring statistics for a specific user."""
    # Ensure the user can only access their own stats
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only view your own stats"
        )
    
    hiring_service = HiringService(db)
    return hiring_service.get_user_hiring_stats(user_id)


@router.get("/stats/agent/{agent_id}")
def get_agent_hiring_stats(agent_id: str, db: Session = Depends(get_session_dependency)):
    """Get hiring statistics for an agent."""
    hiring_service = HiringService(db)
    stats = hiring_service.get_hiring_stats(agent_id=agent_id)
    
    return stats


@router.get("/active/list")
def get_active_hirings(db: Session = Depends(get_session_dependency)):
    """Get all active hirings."""
    hiring_service = HiringService(db)
    hirings = hiring_service.get_active_hirings()
    
    result = []
    for hiring in hirings:
        # Dynamically calculate execution count for each hiring
        from ..models.execution import Execution
        execution_count = db.query(Execution).filter(
            Execution.hiring_id == hiring.id
        ).count()
        
        result.append({
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "user_id": hiring.user_id,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": execution_count,  # Use dynamic count
        })
    
    return result


@router.get("/stats/global")
def get_global_hiring_stats(db: Session = Depends(get_session_dependency)):
    """Get global hiring statistics for the entire system."""
    hiring_service = HiringService(db)
    stats = hiring_service.get_hiring_stats()  # No filters = global stats
    
    return stats