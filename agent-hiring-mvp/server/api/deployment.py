"""Deployment API endpoints for ACP agent management."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..database import get_db
from ..services.deployment_service import DeploymentService
from ..services.function_deployment_service import FunctionDeploymentService

from ..models.deployment import AgentDeployment
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/deployment", tags=["deployment"])


@router.post("/create/{hiring_id}")
def create_deployment(
    hiring_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new deployment for a hired ACP agent."""
    
    # Load and validate hiring ownership
    hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure user owns the hiring (or is admin)
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only create deployments for your own hirings"
        )
    
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
    
    # Use asyncio.create_task for async operations
    task = asyncio.create_task(deployment_service.build_and_deploy(deployment_id))
    
    # Store the task reference to prevent garbage collection
    if not hasattr(create_deployment, '_background_tasks'):
        create_deployment._background_tasks = {}
    create_deployment._background_tasks[deployment_id] = task
    
    return {
        "deployment_id": deployment_id,
        "status": "deployment_started",
        "proxy_endpoint": result["proxy_endpoint"],
        "message": "Deployment started. Check status for progress."
    }


@router.get("/status/{deployment_id}")
def get_deployment_status(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get deployment status."""
    # Get deployment to check ownership
    deployment = db.query(AgentDeployment).filter(AgentDeployment.deployment_id == deployment_id).first()
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Get hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == deployment.hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure user owns the deployment (or is admin)
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only check status of your own deployments"
        )
    
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
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop a deployment."""
    deployment_service = DeploymentService(db)
    
    # Get deployment to check ownership
    deployment = db.query(AgentDeployment).filter(AgentDeployment.deployment_id == deployment_id).first()
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Get hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == deployment.hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure user owns the deployment (or is admin)
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only stop your own deployments"
        )
    
    result = deployment_service.stop_deployment(deployment_id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/restart/{deployment_id}")
def restart_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Restart a stopped deployment."""
    deployment_service = DeploymentService(db)
    
    # Get deployment to check ownership
    deployment = db.query(AgentDeployment).filter(AgentDeployment.deployment_id == deployment_id).first()
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Get hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == deployment.hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure user owns the deployment (or is admin)
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only restart your own deployments"
        )
    
    # Check if deployment exists and is stopped
    status_result = deployment_service.get_deployment_status(deployment_id)
    if "error" in status_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=status_result["error"]
        )
    
    # Start restart process in background
    background_tasks.add_task(
        deployment_service.restart_deployment,
        deployment_id
    )
    
    return {
        "deployment_id": deployment_id,
        "status": "restart_started",
        "message": "Deployment restart started. Check status for progress."
    }


@router.get("/health/{deployment_id}")
async def health_check(
    deployment_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform health check on deployment."""
    # Get deployment to check ownership
    deployment = db.query(AgentDeployment).filter(AgentDeployment.deployment_id == deployment_id).first()
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Get hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == deployment.hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure user owns the deployment (or is admin)
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only check health of your own deployments"
        )
    
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
    agent_id: Optional[str] = None,
    deployment_status: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List deployments with optional filtering by agent ID and status."""
    deployment_service = DeploymentService(db)
    
    try:
        # Get all deployments and filter by user ownership
        all_deployments = deployment_service.list_deployments(agent_id, deployment_status)
            
        # Filter to only show user's own deployments
        user_deployments = []
        for deployment in all_deployments:
            # Get hiring to check ownership
            hiring = db.query(Hiring).filter(Hiring.id == deployment.get('hiring_id')).first()
            if hiring and hiring.user_id == current_user.id:
                user_deployments.append(deployment)
                
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    return {
        "deployments": user_deployments,
        "total": len(user_deployments)
    }


@router.get("/hiring/{hiring_id}")
def get_deployment_by_hiring(
    hiring_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get deployment for a specific hiring."""
    # Get the hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure the user can only access their own hirings
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own hirings"
        )
    
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Get agent type to determine which service to use
    agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
    
    if agent and agent.agent_type == "function":
        # Use function deployment service for function agents
        deployment_service = FunctionDeploymentService(db)
        return deployment_service.get_function_deployment_status(deployment.deployment_id)
    else:
        # Use regular deployment service for ACP agents
        deployment_service = DeploymentService(db)
        return deployment_service.get_deployment_status(deployment.deployment_id)


@router.post("/hiring/{hiring_id}/start-build")
async def start_deployment_build(
    hiring_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start the build and deploy process for a hiring."""
    # Get the hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure the user can only access their own hirings
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own hirings"
        )
    
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Get agent type to determine which service to use
    agent = db.query(Agent).filter(Agent.id == deployment.agent_id).first()
    
    try:
        if agent and agent.agent_type == "function":
            # Use function deployment service for function agents
            deployment_service = FunctionDeploymentService(db)
            result = await deployment_service.build_and_deploy_function(deployment.deployment_id)
        else:
            # Use regular deployment service for ACP agents
            deployment_service = DeploymentService(db)
            result = await deployment_service.build_and_deploy(deployment.deployment_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Build failed: {result['error']}"
            )
        
        return {
            "message": "Build and deploy started successfully",
            "deployment_id": deployment.deployment_id,
            "status": "building"
        }
        
    except Exception as e:
        logger.error(f"Failed to start build for deployment {deployment.deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start build: {str(e)}"
        )


# REMOVED: /rebuild endpoint - duplicate of /restart
# Use /restart endpoint instead for better safety and consistency


@router.post("/reconcile")
def reconcile_all_deployments(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger deployment reconciliation for all deployments."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        result = reconciliation_service.reconcile_all_deployments()
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return {
            "message": "Deployment reconciliation completed",
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Failed to reconcile deployments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconcile deployments: {str(e)}"
        )


@router.post("/reconcile/{deployment_id}")
def reconcile_deployment(
    deployment_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger reconciliation for a specific deployment."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        result = reconciliation_service.reconcile_deployment_by_id(deployment_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "message": "Deployment reconciliation completed",
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Failed to reconcile deployment {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconcile deployment: {str(e)}"
        )


@router.get("/health-summary")
def get_deployment_health_summary(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a summary of deployment health status."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        result = reconciliation_service.get_deployment_health_summary()
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get deployment health summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment health summary: {str(e)}"
        )


@router.get("/hiring-consistency")
def validate_hiring_deployment_consistency(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate consistency between hiring status and deployment status."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        result = reconciliation_service.validate_hiring_deployment_consistency()
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to validate hiring-deployment consistency: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate hiring-deployment consistency: {str(e)}"
        )


# Note: Diagnostic and reconciliation endpoints have been moved to diagnostic.py 