"""Deployment API endpoints for ACP agent management."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..database import get_db
from ..services.deployment_service import DeploymentService
from ..services.function_deployment_service import FunctionDeploymentService
from ..services.deployment_reconciliation_service import DeploymentReconciliationService
from ..models.deployment import AgentDeployment
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/deployment", tags=["deployment"])


@router.post("/create/{hiring_id}")
def create_deployment(
    hiring_id: int,
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


@router.post("/restart/{deployment_id}")
def restart_deployment(
    deployment_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Restart a stopped deployment."""
    deployment_service = DeploymentService(db)
    
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
    agent_id: Optional[str] = None,
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


# =============================================================================
# SYSTEM ANALYSIS AND RECONCILIATION ENDPOINTS (Available to all authenticated users)
# =============================================================================

@router.get("/admin/analysis")
def get_system_analysis(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive system analysis (Available to all authenticated users - READ-ONLY)."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        
        # Collect all analysis data (READ-ONLY)
        analysis_data = {
            "deployment_health": reconciliation_service.get_deployment_health_summary(),
            "hiring_consistency": reconciliation_service.validate_hiring_deployment_consistency(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "This is READ-ONLY analysis data. No changes are made to the system."
        }
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"Failed to get system analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system analysis: {str(e)}"
        )

@router.get("/admin/drilldown/hirings")
def get_hirings_drilldown(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed hiring information for system analysis drill-down (Available to all authenticated users)."""
    try:
        from ..models.hiring import Hiring
        from ..models.agent import Agent
        from ..models.user import User
        
        # Get all hirings with related data
        hirings = db.query(Hiring).join(Agent).join(User).all()
        
        hiring_details = []
        for hiring in hirings:
            # Get deployment info if exists
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            hiring_detail = {
                "hiring_id": hiring.id,
                "agent_id": hiring.agent_id,
                "agent_name": hiring.agent.name if hiring.agent else "Unknown",
                "agent_type": hiring.agent.agent_type if hiring.agent else "unknown",
                "user_id": hiring.user_id,
                "username": hiring.user.username if hiring.user else "Unknown",
                "email": hiring.user.email if hiring.user else "Unknown",
                "status": hiring.status,
                "billing_cycle": hiring.billing_cycle,
                "hired_at": hiring.hired_at.isoformat() if hiring.hired_at else None,
                "expires_at": hiring.expires_at.isoformat() if hiring.expires_at else None,
                "total_executions": hiring.total_executions,
                "last_executed_at": hiring.last_executed_at.isoformat() if hiring.last_executed_at else None,
                "deployment": None
            }
            
            if deployment:
                hiring_detail["deployment"] = {
                    "deployment_id": deployment.deployment_id,
                    "status": deployment.status,
                    "container_name": deployment.container_name,
                    "container_id": deployment.container_id,
                    "proxy_endpoint": deployment.proxy_endpoint,
                    "external_port": deployment.external_port,
                    "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
                    "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
                    "is_healthy": deployment.is_healthy
                }
            
            hiring_details.append(hiring_detail)
        
        return {
            "total_hirings": len(hiring_details),
            "hirings": hiring_details
        }
        
    except Exception as e:
        logger.error(f"Failed to get hirings drill-down: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hirings drill-down: {str(e)}"
        )

@router.get("/admin/drilldown/deployments")
def get_deployments_drilldown(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed deployment information for system analysis drill-down (Available to all authenticated users)."""
    try:
        from ..models.hiring import Hiring
        from ..models.agent import Agent
        from ..models.user import User
        
        # Get all deployments with related data
        deployments = db.query(AgentDeployment).join(Hiring).join(Agent).join(User).all()
        
        deployment_details = []
        for deployment in deployments:
            deployment_detail = {
                "deployment_id": deployment.deployment_id,
                "hiring_id": deployment.hiring_id,
                "agent_id": deployment.agent_id,
                "agent_name": deployment.hiring.agent.name if deployment.hiring and deployment.hiring.agent else "Unknown",
                "agent_type": deployment.hiring.agent.agent_type if deployment.hiring and deployment.hiring.agent else "unknown",
                "user_id": deployment.hiring.user_id if deployment.hiring else None,
                "username": deployment.hiring.user.username if deployment.hiring and deployment.hiring.user else "Unknown",
                "status": deployment.status,
                "container_name": deployment.container_name,
                "container_id": deployment.container_id,
                "proxy_endpoint": deployment.proxy_endpoint,
                "external_port": deployment.external_port,
                "started_at": deployment.started_at.isoformat() if deployment.started_at else None,
                "stopped_at": deployment.stopped_at.isoformat() if deployment.stopped_at else None,
                "is_healthy": deployment.is_healthy,
                "hiring_status": deployment.hiring.status if deployment.hiring else "Unknown"
            }
            
            deployment_details.append(deployment_detail)
        
        return {
            "total_deployments": len(deployment_details),
            "deployments": deployment_details
        }
        
    except Exception as e:
        logger.error(f"Failed to get deployments drill-down: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployments drill-down: {str(e)}"
        )

@router.get("/admin/drilldown/containers")
def get_containers_drilldown(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed Docker container information for system analysis drill-down (Available to all authenticated users)."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        
        # Get all AgentHub containers
        all_containers = reconciliation_service.docker_client.containers.list(all=True)
        containers = [c for c in all_containers if c.name.startswith('aghub-')]
        
        container_details = []
        for container in containers:
            # Check if container has corresponding deployment
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.container_name == container.name
            ).first()
            
            container_detail = {
                "name": container.name,
                "id": container.id[:12],  # Short ID
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else container.image.id[:12],
                "created": container.attrs.get('Created', 'Unknown'),
                "ports": container.attrs.get('NetworkSettings', {}).get('Ports', {}),
                "has_deployment_record": deployment is not None,
                "deployment_info": None
            }
            
            if deployment:
                # Get related hiring and agent info
                hiring = db.query(Hiring).filter(Hiring.id == deployment.hiring_id).first()
                if hiring and hiring.agent:
                    container_detail["deployment_info"] = {
                        "deployment_id": deployment.deployment_id,
                        "hiring_id": deployment.hiring_id,
                        "agent_name": hiring.agent.name,
                        "agent_type": hiring.agent.agent_type,
                        "deployment_status": deployment.status,
                        "hiring_status": hiring.status
                    }
            
            container_details.append(container_detail)
        
        return {
            "total_containers": len(container_details),
            "containers": container_details
        }
        
    except Exception as e:
        logger.error(f"Failed to get containers drill-down: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get containers drill-down: {str(e)}"
        )


@router.post("/admin/reconcile")
def admin_reconcile_deployments(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint to reconcile deployment states (Available to all authenticated users)."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        
        # Perform the actual reconciliation
        result = reconciliation_service.reconcile_all_deployments()
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return {
            "message": "Deployment reconciliation completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Reconciliation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconcile deployments: {str(e)}"
        )


@router.post("/admin/reconcile/{deployment_id}")
def admin_reconcile_specific_deployment(
    deployment_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Endpoint to reconcile a specific deployment (Available to all authenticated users)."""
    try:
        reconciliation_service = DeploymentReconciliationService(db)
        
        # Perform reconciliation for specific deployment
        result = reconciliation_service.reconcile_deployment_by_id(deployment_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return {
            "message": f"Deployment {deployment_id} reconciliation completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": result
        }
        
    except Exception as e:
        logger.error(f"Reconciliation of deployment {deployment_id} failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconcile deployment: {str(e)}"
        ) 