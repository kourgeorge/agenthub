"""Metrics API endpoints for Prometheus monitoring and container metrics."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.deployment import AgentDeployment
from ..services.prometheus_metrics import metrics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format for scraping."""
    try:
        metrics = metrics_service.get_metrics()
        return Response(
            content=metrics,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error(f"Error getting Prometheus metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/containers")
async def get_container_metrics_summary():
    """Get a summary of container metrics."""
    try:
        summary = metrics_service.get_container_metrics_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting container metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get container metrics: {str(e)}"
        )


@router.get("/containers/{deployment_id}")
async def get_container_metrics(
    deployment_id: str,
    db: Session = Depends(get_db)
):
    """Get metrics for a specific container deployment."""
    try:
        # Get deployment info
        deployment = db.query(AgentDeployment).filter(
            AgentDeployment.deployment_id == deployment_id
        ).first()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
        
        # Collect metrics for this container
        deployment_info = {
            'container_name': deployment.container_name,
            'agent_id': deployment.agent_id,
            'hiring_id': deployment.hiring_id,
            'deployment_type': deployment.deployment_type
        }
        
        metrics_service.collect_container_metrics(deployment_info)
        
        # Get the collected metrics
        if deployment.container_name in metrics_service.container_metrics:
            return metrics_service.container_metrics[deployment.container_name]
        else:
            return {"error": "No metrics available for this container"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting container metrics for {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get container metrics: {str(e)}"
        )


@router.post("/collect")
async def collect_all_metrics():
    """Trigger collection of all container metrics."""
    try:
        # Collect system metrics
        metrics_service.collect_system_metrics()
        
        # Get all active deployments and collect their metrics
        from ..database import get_db
        db = next(get_db())
        
        deployments = db.query(AgentDeployment).filter(
            AgentDeployment.status.in_(["running", "active"])
        ).all()
        
        collected_count = 0
        for deployment in deployments:
            if deployment.container_name:
                deployment_info = {
                    'container_name': deployment.container_name,
                    'agent_id': deployment.agent_id,
                    'hiring_id': deployment.hiring_id,
                    'deployment_type': deployment.deployment_type
                }
                metrics_service.collect_container_metrics(deployment_info)
                collected_count += 1
        
        return {
            "message": "Metrics collection completed",
            "deployments_processed": collected_count,
            "total_metrics": len(metrics_service.container_metrics)
        }
        
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect metrics: {str(e)}"
        )


@router.get("/system")
async def get_system_metrics():
    """Get system-wide container metrics."""
    try:
        # Collect fresh system metrics
        metrics_service.collect_system_metrics()
        
        # Get container counts by type
        containers = metrics_service.docker_client.containers.list(all=True)
        
        system_metrics = {
            'total_containers': len(containers),
            'containers_by_type': {},
            'resource_summary': {
                'total_cpu_percent': 0.0,
                'total_memory_bytes': 0,
                'total_memory_limit_bytes': 0
            }
        }
        
        # Group containers by type
        for container in containers:
            container_type = 'unknown'
            if container.name.startswith('acp-'):
                container_type = 'acp'
            elif container.name.startswith('func-'):
                container_type = 'function'
            elif container.name.startswith('persis-'):
                container_type = 'persistent'
            
            if container_type not in system_metrics['containers_by_type']:
                system_metrics['containers_by_type'][container_type] = {
                    'total': 0,
                    'running': 0,
                    'stopped': 0
                }
            
            system_metrics['containers_by_type'][container_type]['total'] += 1
            if container.status == 'running':
                system_metrics['containers_by_type'][container_type]['running'] += 1
            else:
                system_metrics['containers_by_type'][container_type]['stopped'] += 1
        
        # Add resource summary from collected metrics
        summary = metrics_service.get_container_metrics_summary()
        system_metrics['resource_summary'] = summary.get('resource_usage', {})
        
        return system_metrics
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_old_metrics(max_age_hours: int = 24):
    """Clean up old container metrics."""
    try:
        metrics_service.cleanup_old_metrics(max_age_hours)
        return {
            "message": "Metrics cleanup completed",
            "max_age_hours": max_age_hours,
            "remaining_metrics": len(metrics_service.container_metrics)
        }
    except Exception as e:
        logger.error(f"Error cleaning up metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup metrics: {str(e)}"
        )
