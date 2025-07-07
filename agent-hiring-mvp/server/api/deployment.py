"""Deployment API endpoints for ACP agent management."""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.deployment_service import DeploymentService
from ..models.deployment import AgentDeployment

router = APIRouter(prefix="/deployment", tags=["deployment"])


@router.post("/create/{hiring_id}")
def create_deployment(
    hiring_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new deployment for a hired ACP agent."""
    deployment_service = DeploymentService(db)
    
    # Create deployment record
    result = deployment_service.create_deployment(hiring_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    # Start build and deploy process in background
    deployment_id = result["deployment_id"]
    background_tasks.add_task(
        deployment_service.build_and_deploy,
        deployment_id
    )
    
    return {
        "deployment_id": deployment_id,
        "status": "deployment_started",
        "proxy_endpoint": result["proxy_endpoint"],
        "message": "Deployment started. Check status for progress."
    }


@router.get("/status/{deployment_id}")
def get_deployment_status(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Get deployment status."""
    deployment_service = DeploymentService(db)
    result = deployment_service.get_deployment_status(deployment_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return result


@router.post("/stop/{deployment_id}")
def stop_deployment(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Stop a deployment."""
    deployment_service = DeploymentService(db)
    result = deployment_service.stop_deployment(deployment_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.get("/health/{deployment_id}")
async def health_check(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Perform health check on deployment."""
    deployment_service = DeploymentService(db)
    result = await deployment_service.health_check(deployment_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    return result


@router.get("/list")
def list_deployments(
    agent_id: Optional[int] = None,
    deployment_status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List deployments with optional filtering by agent ID and status."""
    deployment_service = DeploymentService(db)
    
    try:
        deployments = deployment_service.list_deployments(agent_id, deployment_status)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return {
        "deployments": deployments,
        "total": len(deployments)
    }


@router.get("/hiring/{hiring_id}")
def get_deployment_by_hiring(
    hiring_id: int,
    db: Session = Depends(get_db)
):
    """Get deployment for a specific hiring."""
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    deployment_service = DeploymentService(db)
    return deployment_service.get_deployment_status(deployment.deployment_id)


@router.post("/rebuild/{deployment_id}")
def rebuild_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Rebuild and redeploy an agent."""
    deployment_service = DeploymentService(db)
    
    # Stop existing deployment
    stop_result = deployment_service.stop_deployment(deployment_id)
    if "error" in stop_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop existing deployment: {stop_result['error']}"
        )
    
    # Start rebuild process
    background_tasks.add_task(
        deployment_service.build_and_deploy,
        deployment_id
    )
    
    return {
        "deployment_id": deployment_id,
        "status": "rebuild_started",
        "message": "Rebuild started. Check status for progress."
    } 