"""System diagnostic and monitoring API endpoints."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..database import get_db
from ..services.deployment_reconciliation_service import DeploymentReconciliationService
from ..models.deployment import AgentDeployment
from ..models.agent import Agent
from ..models.hiring import Hiring
from ..models.user import User
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


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


@router.get("/admin/hirings")
def get_hirings_diagnostic(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed hiring information for system diagnostics (Available to all authenticated users)."""
    try:
        # Get all hirings with related data
        hirings = db.query(Hiring).join(Agent).join(User).all()
        
        hiring_details = []
        for hiring in hirings:
            # Get deployment info if exists
            deployment = db.query(AgentDeployment).filter(
                AgentDeployment.hiring_id == hiring.id
            ).first()
            
            # Dynamically calculate execution count instead of using removed field
            from ..models.execution import Execution
            execution_count = db.query(Execution).filter(
                Execution.hiring_id == hiring.id
            ).count()
            
            hiring_detail = {
                "id": hiring.id,
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
                "total_executions": execution_count,  # Use dynamic count
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
        logger.error(f"Failed to get hirings diagnostic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hirings diagnostic: {str(e)}"
        )


@router.get("/admin/deployments")
def get_deployments_diagnostic(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed deployment information for system diagnostics (Available to all authenticated users)."""
    try:
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
        logger.error(f"Failed to get deployments diagnostic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployments diagnostic: {str(e)}"
        )


@router.get("/admin/containers")
def get_containers_diagnostic(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed Docker container information for system diagnostics (Available to all authenticated users)."""
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
        logger.error(f"Failed to get containers diagnostic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get containers diagnostic: {str(e)}"
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
