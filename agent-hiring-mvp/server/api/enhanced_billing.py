"""
Enhanced billing API endpoints for container resource cost tracking and AWS EC2-style billing.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.enhanced_billing_service import EnhancedBillingService
from ..models.user import User
from ..middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enhanced-billing", tags=["enhanced-billing"])


class CostEstimateRequest(BaseModel):
    """Request model for cost estimation"""
    deployment_type: str
    duration_hours: float
    avg_cpu_percent: float = 50.0
    avg_memory_gb: float = 1.0
    
    @validator('deployment_type')
    def validate_deployment_type(cls, v):
        if v not in ['acp', 'function', 'persistent']:
            raise ValueError('deployment_type must be one of: acp, function, persistent')
        return v
    
    @validator('duration_hours')
    def validate_duration_hours(cls, v):
        if v <= 0:
            raise ValueError('duration_hours must be positive')
        return v
    
    @validator('avg_cpu_percent')
    def validate_cpu_percent(cls, v):
        if v < 0 or v > 100:
            raise ValueError('avg_cpu_percent must be between 0 and 100')
        return v
    
    @validator('avg_memory_gb')
    def validate_memory_gb(cls, v):
        if v <= 0:
            raise ValueError('avg_memory_gb must be positive')
        return v


@router.get("/summary/{user_id}")
async def get_user_billing_summary(
    user_id: int,
    months: int = Query(1, description="Number of months to fetch", ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive billing summary including container resource costs."""
    try:
        # Ensure user can only access their own billing or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own billing information"
            )
        
        billing_service = EnhancedBillingService(db)
        summary = await billing_service.get_user_billing_summary(user_id, months)
        
        if "error" in summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=summary["error"]
            )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting billing summary for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get billing summary: {str(e)}"
        )


@router.get("/daily-usage/{user_id}")
async def get_user_daily_usage(
    user_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed daily usage for a specific user and date."""
    try:
        # Ensure user can only access their own usage or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own usage information"
            )
        
        # Parse date
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        billing_service = EnhancedBillingService(db)
        daily_usage = await billing_service.get_user_daily_usage(user_id, parsed_date)
        
        if "error" in daily_usage:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=daily_usage["error"]
            )
        
        return daily_usage
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting daily usage for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily usage: {str(e)}"
        )


@router.post("/cost-estimate")
async def get_deployment_cost_estimate(
    request: CostEstimateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cost estimate for a deployment before it starts."""
    try:
        billing_service = EnhancedBillingService(db)
        estimate = await billing_service.get_deployment_cost_estimate(
            request.deployment_type,
            request.duration_hours,
            request.avg_cpu_percent,
            request.avg_memory_gb
        )
        
        if "error" in estimate:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=estimate["error"]
            )
        
        return estimate
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cost estimate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost estimate: {str(e)}"
        )


@router.get("/budget-check/{user_id}")
async def check_budget_limit(
    user_id: int,
    estimated_cost: float = Query(..., description="Estimated cost to check against budget"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has sufficient budget for estimated costs."""
    try:
        # Ensure user can only access their own budget or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own budget information"
            )
        
        if estimated_cost < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estimated cost must be non-negative"
            )
        
        billing_service = EnhancedBillingService(db)
        budget_check = await billing_service.check_budget_limit(user_id, estimated_cost)
        
        return budget_check
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking budget for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check budget: {str(e)}"
        )


@router.get("/monthly-breakdown/{user_id}")
async def get_monthly_breakdown(
    user_id: int,
    year: int = Query(..., description="Year to fetch"),
    month: int = Query(..., description="Month to fetch (1-12)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get monthly billing breakdown for a specific user and month."""
    try:
        # Ensure user can only access their own billing or is admin
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own billing information"
            )
        
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be between 1 and 12"
            )
        
        from ..services.resource_usage_tracker import ResourceUsageTracker
        resource_tracker = ResourceUsageTracker(db)
        monthly_billing = resource_tracker.get_user_monthly_billing(user_id, year, month)
        
        if not monthly_billing:
            return {
                "user_id": user_id,
                "year": year,
                "month": month,
                "total_cost": 0.0,
                "total_cpu_hours": 0.0,
                "total_memory_gb_hours": 0.0,
                "total_network_gb": 0.0,
                "total_requests": 0,
                "daily_breakdown": [],
                "deployment_breakdown": {}
            }
        
        return monthly_billing
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monthly breakdown for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monthly breakdown: {str(e)}"
        )


@router.get("/deployment-costs/{deployment_id}")
async def get_deployment_costs(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed cost breakdown for a specific deployment."""
    try:
        from ..models.deployment import AgentDeployment
        from ..models.container_resource_usage import ContainerResourceUsage
        
        # Get deployment info
        deployment = db.query(AgentDeployment).filter(
            AgentDeployment.deployment_id == deployment_id
        ).first()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deployment not found"
            )
        
        # Ensure user can only access their own deployments or is admin
        if deployment.hiring.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only access your own deployments"
            )
        
        # Get resource usage for this deployment
        resource_usage = db.query(ContainerResourceUsage).filter(
            ContainerResourceUsage.deployment_id == deployment_id
        ).order_by(ContainerResourceUsage.snapshot_timestamp.desc()).all()
        
        if not resource_usage:
            return {
                "deployment_id": deployment_id,
                "agent_id": deployment.agent_id,
                "deployment_type": deployment.deployment_type,
                "total_cost": 0.0,
                "total_snapshots": 0,
                "cost_breakdown": {
                    "cpu_cost": 0.0,
                    "memory_cost": 0.0,
                    "network_cost": 0.0,
                    "storage_cost": 0.0
                },
                "resource_usage": {
                    "total_cpu_hours": 0.0,
                    "total_memory_gb_hours": 0.0,
                    "total_network_gb": 0.0
                },
                "snapshots": []
            }
        
        # Calculate totals
        total_cost = sum(r.total_cost for r in resource_usage)
        total_cpu_hours = sum(r.cpu_usage_percent for r in resource_usage) / 100.0 * (30/3600)
        total_memory_gb_hours = sum(r.memory_usage_bytes for r in resource_usage) / (1024**3) * (30/3600)
        total_network_gb = sum(r.network_rx_bytes + r.network_tx_bytes for r in resource_usage) / (1024**3)
        
        # Cost breakdown
        cost_breakdown = {
            "cpu_cost": sum(r.cpu_cost for r in resource_usage),
            "memory_cost": sum(r.memory_cost for r in resource_usage),
            "network_cost": sum(r.network_cost for r in resource_usage),
            "storage_cost": sum(r.storage_cost for r in resource_usage)
        }
        
        # Format snapshots
        snapshots = []
        for usage in resource_usage:
            snapshots.append({
                "timestamp": usage.snapshot_timestamp.isoformat(),
                "cpu_percent": usage.cpu_usage_percent,
                "memory_gb": usage.memory_usage_bytes / (1024**3),
                "network_gb": (usage.network_rx_bytes + usage.network_tx_bytes) / (1024**3),
                "total_cost": usage.total_cost,
                "container_status": usage.container_status
            })
        
        return {
            "deployment_id": deployment_id,
            "agent_id": deployment.agent_id,
            "deployment_type": deployment.deployment_type,
            "total_cost": round(total_cost, 6),
            "total_snapshots": len(resource_usage),
            "cost_breakdown": {
                "cpu_cost": round(cost_breakdown["cpu_cost"], 6),
                "memory_cost": round(cost_breakdown["memory_cost"], 6),
                "network_cost": round(cost_breakdown["network_cost"], 6),
                "storage_cost": round(cost_breakdown["storage_cost"], 6)
            },
            "resource_usage": {
                "total_cpu_hours": round(total_cpu_hours, 4),
                "total_memory_gb_hours": round(total_memory_gb_hours, 4),
                "total_network_gb": round(total_network_gb, 4)
            },
            "snapshots": snapshots
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment costs for {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment costs: {str(e)}"
        )


@router.get("/pricing")
async def get_resource_pricing(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current resource pricing configuration."""
    try:
        from ..services.resource_usage_tracker import ResourceUsageTracker
        
        resource_tracker = ResourceUsageTracker(db)
        pricing = resource_tracker.pricing
        
        # Format pricing for API response
        formatted_pricing = {}
        for resource_type, deployment_pricing in pricing.items():
            formatted_pricing[resource_type] = {
                "unit": "per_hour" if resource_type in ["cpu", "memory", "storage"] else "per_gb",
                "deployment_types": deployment_pricing
            }
        
        return {
            "pricing": formatted_pricing,
            "currency": "USD",
            "billing_model": "AWS EC2-style hourly billing",
            "collection_interval": "30 seconds",
            "description": "Competitive pricing based on AWS EC2 rates"
        }
        
    except Exception as e:
        logger.error(f"Error getting resource pricing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resource pricing: {str(e)}"
        )
