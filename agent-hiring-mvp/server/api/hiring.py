"""Hiring API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.config import get_session_dependency
from ..services.hiring_service import HiringService, HiringCreateRequest
from ..models.hiring import Hiring, HiringStatus
from ..models.deployment import AgentDeployment
from ..middleware.auth import get_current_user, get_current_user_optional, require_same_user

router = APIRouter(prefix="/hiring", tags=["hiring"])


@router.post("/", response_model=dict)
def create_hiring(
    hiring_data: HiringCreateRequest,
    current_user = Depends(get_current_user_optional),
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
        response["message"] += ". ACP agent deployment is starting in the background."
        response["deployment_status"] = "starting"
    
    # Add deployment status for function agents
    elif agent and agent.agent_type == "function":
        response["message"] += ". Function agent Docker container is being prepared."
        response["deployment_status"] = "starting"
        
        # Check if deployment already exists
        deployment = db.query(AgentDeployment).filter(
            AgentDeployment.hiring_id == hiring.id
        ).first()
        
        if deployment:
            response["deployment"] = {
                "deployment_id": deployment.deployment_id,
                "status": deployment.status,
                "container_id": deployment.container_id,
                "container_name": deployment.container_name,
                "started_at": deployment.started_at.isoformat() if deployment.started_at else None
            }
    
    return response


@router.get("/user", response_model=List[dict])
def get_current_user_hirings(
    status: Optional[str] = None,
    current_user = Depends(get_current_user_optional),
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
        hiring_data = {
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "status": hiring.status,
            "billing_cycle": hiring.billing_cycle,
            "hired_at": hiring.hired_at.isoformat(),
            "created_at": hiring.hired_at.isoformat(),  # Alias for frontend compatibility
            "total_executions": hiring.total_executions,
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
    current_user = Depends(get_current_user_optional),
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
        hiring_data = {
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": hiring.total_executions,
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


@router.get("/{hiring_id}", response_model=dict)
def get_hiring(
    hiring_id: int, 
    current_user = Depends(get_current_user_optional),
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
    
    # Get deployment information
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    response = {
        "id": hiring.id,
        "agent_id": hiring.agent_id,
        "user_id": hiring.user_id,
        "status": hiring.status,
        "hired_at": hiring.hired_at.isoformat(),
        "expires_at": hiring.expires_at.isoformat() if hiring.expires_at else None,
        "config": hiring.config,
        "state": hiring.state,
        "total_executions": hiring.total_executions,
        "last_executed_at": hiring.last_executed_at.isoformat() if hiring.last_executed_at else None,
    }
    
    # Add agent information including agent_type
    if hiring.agent:
        response.update({
            "agent_name": hiring.agent.name,
            "agent_type": hiring.agent.agent_type,
            "agent_description": hiring.agent.description,
        })
    
    # Add deployment information if available
    if deployment:
        response["deployment"] = {
            "deployment_id": deployment.deployment_id,
            "status": deployment.status,
            "container_id": deployment.container_id,
            "container_name": deployment.container_name,
            "deployment_type": deployment.deployment_type,
            "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
            "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
            "is_healthy": deployment.is_healthy,
            "internal_port": deployment.internal_port,
            "external_port": deployment.external_port
        }
    
    return response


@router.get("/agent/{agent_id}", response_model=List[dict])
def get_agent_hirings(
    agent_id: str,
    status: Optional[str] = None,
    current_user = Depends(get_current_user_optional),
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
    
    return [
        {
            "id": hiring.id,
            "user_id": hiring.user_id,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": hiring.total_executions,
        }
        for hiring in user_hirings
    ]


@router.put("/{hiring_id}/activate")
def activate_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_session_dependency)
):
    """Activate a hiring."""
    hiring_service = HiringService(db)
    
    # First check if the hiring exists and belongs to the current user
    hiring = hiring_service.get_hiring(hiring_id)
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only modify your own hirings"
        )
    
    result = hiring_service.activate_hiring(hiring_id, notes)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    response = {
        "hiring_id": result["hiring_id"],
        "agent_id": result["agent_id"],
        "agent_name": result["agent_name"],
        "agent_type": result["agent_type"],
        "status": result["status"],
        "message": "Hiring activated successfully"
    }
    
    # Add deployment information for ACP agents
    if result.get("deployment"):
        response["deployment"] = result["deployment"]
        response["message"] += ". ACP agent deployment is now active."
    
    return response


@router.put("/{hiring_id}/suspend")
def suspend_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_session_dependency)
):
    """Suspend a hiring and automatically stop associated deployments."""
    hiring_service = HiringService(db)
    
    # First check if the hiring exists and belongs to the current user
    hiring = hiring_service.get_hiring(hiring_id)
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only modify your own hirings"
        )
    
    hiring = hiring_service.suspend_hiring(hiring_id, notes)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    return {
        "id": hiring.id,
        "status": hiring.status,
        "message": "Hiring suspended successfully. Associated deployments have been stopped."
    }


@router.put("/{hiring_id}/cancel")
def cancel_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    timeout: Optional[int] = 60,
    current_user = Depends(get_current_user_optional),
    db: Session = Depends(get_session_dependency)
):
    """Cancel a hiring and automatically stop associated deployments."""
    hiring_service = HiringService(db)
    
    # First check the current status and ownership
    current_hiring = hiring_service.get_hiring(hiring_id)
    if not current_hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    if current_hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only modify your own hirings"
        )
    
    # Always perform the cancellation (this will clean up containers even if already cancelled)
    hiring = hiring_service.cancel_hiring(hiring_id, notes)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Check if it was already cancelled
    was_already_cancelled = current_hiring.status == HiringStatus.CANCELLED.value
    
    if was_already_cancelled:
        return {
            "id": hiring.id,
            "status": hiring.status,
            "message": "Hiring was already cancelled. Any remaining containers have been cleaned up.",
            "already_cancelled": True
        }
    else:
        return {
            "id": hiring.id,
            "status": hiring.status,
            "message": "Hiring cancelled successfully. All resources have been terminated.",
            "already_cancelled": False
        }


@router.get("/stats/user/{user_id}")
def get_user_hiring_stats(
    user_id: int, 
    current_user = Depends(get_current_user_optional),
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
    
    return [
        {
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "user_id": hiring.user_id,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": hiring.total_executions,
        }
        for hiring in hirings
    ]


 