"""
Enhanced billing service that integrates container resource costs with traditional billing.
Provides AWS EC2-style hourly billing for agent deployments.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .resource_usage_tracker import ResourceUsageTracker
from ..models.container_resource_usage import ContainerResourceUsage, UsageAggregation, AgentActivityLog
from ..models.deployment import AgentDeployment
from ..models.hiring import Hiring
from ..models.user import User
from ..models.resource_usage import UserBudget

logger = logging.getLogger(__name__)


class EnhancedBillingService:
    """Enhanced billing service with container resource cost tracking."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.resource_tracker = ResourceUsageTracker(db_session)
    
    async def get_user_billing_summary(self, user_id: int, months: int = 1) -> Dict[str, Any]:
        """Get comprehensive billing summary including container resource costs."""
        try:
            current_date = datetime.now(timezone.utc)
            
            # Get basic user info
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Get budget information
            budget = self.db.query(UserBudget).filter(UserBudget.user_id == user_id).first()
            
            # Calculate date range
            end_date = current_date
            start_date = end_date - timedelta(days=months * 30)
            
            # Get container resource costs
            container_costs = await self._get_container_resource_costs(user_id, start_date, end_date)
            
            # Get traditional execution costs (if any)
            execution_costs = await self._get_execution_costs(user_id, start_date, end_date)
            
            # Calculate totals
            total_container_cost = sum(deployment["total_cost"] for deployment in container_costs["deployments"])
            total_execution_cost = sum(execution.get("total_cost", 0) for execution in execution_costs)
            total_cost = total_container_cost + total_execution_cost
            
            # Get monthly breakdown
            monthly_breakdown = await self._get_monthly_breakdown(user_id, start_date, end_date)
            
            # Calculate budget utilization
            budget_utilization = 0.0
            remaining_budget = 0.0
            if budget:
                budget_utilization = (total_cost / budget.monthly_budget) * 100 if budget.monthly_budget > 0 else 0
                remaining_budget = max(0, budget.monthly_budget - total_cost)
            
            return {
                "user_id": user_id,
                "username": user.username,
                "billing_period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "months": months
                },
                "cost_summary": {
                    "total_cost": round(total_cost, 6),
                    "container_resource_cost": round(total_container_cost, 6),
                    "execution_cost": round(total_execution_cost, 6),
                    "currency": "USD"
                },
                "resource_usage": {
                    "total_cpu_hours": container_costs["total_cpu_hours"],
                    "total_memory_gb_hours": container_costs["total_memory_gb_hours"],
                    "total_network_gb": container_costs["total_network_gb"],
                    "total_deployments": len(container_costs["deployments"]),
                    "total_requests": container_costs["total_requests"]
                },
                "deployment_breakdown": container_costs["deployments"],
                "monthly_breakdown": monthly_breakdown,
                "budget": {
                    "monthly_budget": budget.monthly_budget if budget else 0.0,
                    "current_usage": total_cost,
                    "remaining_budget": remaining_budget,
                    "utilization_percent": round(budget_utilization, 2)
                },
                "cost_trends": await self._get_cost_trends(user_id, months),
                "generated_at": current_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting billing summary for user {user_id}: {e}")
            return {"error": f"Failed to get billing summary: {str(e)}"}
    
    async def _get_container_resource_costs(self, user_id: int, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get container resource costs for a user in a date range."""
        try:
            # Get all deployments for this user in the date range
            deployments = self.db.query(AgentDeployment).join(Hiring).filter(
                and_(
                    Hiring.user_id == user_id,
                    AgentDeployment.created_at >= start_date,
                    AgentDeployment.created_at <= end_date
                )
            ).all()
            
            deployment_costs = []
            total_cpu_hours = 0.0
            total_memory_gb_hours = 0.0
            total_network_gb = 0.0
            total_requests = 0
            
            for deployment in deployments:
                # Get resource usage for this deployment
                resource_usage = self.db.query(ContainerResourceUsage).filter(
                    and_(
                        ContainerResourceUsage.deployment_id == deployment.deployment_id,
                        ContainerResourceUsage.snapshot_timestamp >= start_date,
                        ContainerResourceUsage.snapshot_timestamp <= end_date
                    )
                ).all()
                
                if resource_usage:
                    # Calculate totals for this deployment
                    deployment_total_cost = sum(r.total_cost for r in resource_usage)
                    deployment_cpu_hours = sum(r.cpu_usage_percent for r in resource_usage) / 100.0 * (30/3600)  # Convert to hours
                    deployment_memory_gb_hours = sum(r.memory_usage_bytes for r in resource_usage) / (1024**3) * (30/3600)
                    deployment_network_gb = sum(r.network_rx_bytes + r.network_tx_bytes for r in resource_usage) / (1024**3)
                    
                    # Get activity count
                    activity_count = self.db.query(AgentActivityLog).filter(
                        and_(
                            AgentActivityLog.deployment_id == deployment.deployment_id,
                            AgentActivityLog.activity_timestamp >= start_date,
                            AgentActivityLog.activity_timestamp <= end_date
                        )
                    ).count()
                    
                    deployment_summary = {
                        "deployment_id": deployment.deployment_id,
                        "agent_id": deployment.agent_id,
                        "deployment_type": deployment.deployment_type,
                        "status": deployment.status,
                        "created_at": deployment.created_at.isoformat(),
                        "total_cost": round(deployment_total_cost, 6),
                        "cpu_hours": round(deployment_cpu_hours, 4),
                        "memory_gb_hours": round(deployment_memory_gb_hours, 4),
                        "network_gb": round(deployment_network_gb, 4),
                        "requests": activity_count,
                        "cost_breakdown": {
                            "cpu_cost": round(sum(r.cpu_cost for r in resource_usage), 6),
                            "memory_cost": round(sum(r.memory_cost for r in resource_usage), 6),
                            "network_cost": round(sum(r.network_cost for r in resource_usage), 6),
                            "storage_cost": round(sum(r.storage_cost for r in resource_usage), 6)
                        }
                    }
                    
                    deployment_costs.append(deployment_summary)
                    
                    # Add to totals
                    total_cpu_hours += deployment_cpu_hours
                    total_memory_gb_hours += deployment_memory_gb_hours
                    total_network_gb += deployment_network_gb
                    total_requests += activity_count
            
            return {
                "deployments": deployment_costs,
                "total_cpu_hours": round(total_cpu_hours, 4),
                "total_memory_gb_hours": round(total_memory_gb_hours, 4),
                "total_network_gb": round(total_network_gb, 4),
                "total_requests": total_requests
            }
            
        except Exception as e:
            logger.error(f"Error getting container resource costs: {e}")
            return {"deployments": [], "total_cpu_hours": 0.0, "total_memory_gb_hours": 0.0, "total_network_gb": 0.0, "total_requests": 0}
    
    async def _get_execution_costs(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get traditional execution costs (for backward compatibility)."""
        try:
            # This would integrate with your existing execution cost tracking
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting execution costs: {e}")
            return []
    
    async def _get_monthly_breakdown(self, user_id: int, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get monthly cost breakdown."""
        try:
            monthly_breakdown = []
            current_date = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            while current_date <= end_date:
                month_start = current_date
                if current_date.month == 12:
                    month_end = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    month_end = current_date.replace(month=current_date.month + 1)
                
                # Get monthly billing for this period
                monthly_billing = self.resource_tracker.get_user_monthly_billing(
                    user_id, current_date.year, current_date.month
                )
                
                if monthly_billing:
                    monthly_breakdown.append({
                        "year": current_date.year,
                        "month": current_date.month,
                        "month_name": current_date.strftime("%B"),
                        "total_cost": round(monthly_billing.get("total_cost", 0.0), 6),
                        "cpu_hours": round(monthly_billing.get("total_cpu_hours", 0.0), 4),
                        "memory_gb_hours": round(monthly_billing.get("total_memory_gb_hours", 0.0), 4),
                        "network_gb": round(monthly_billing.get("total_network_gb", 0.0), 4),
                        "requests": monthly_billing.get("total_requests", 0)
                    })
                
                current_date = month_end
            
            return monthly_breakdown
            
        except Exception as e:
            logger.error(f"Error getting monthly breakdown: {e}")
            return []
    
    async def _get_cost_trends(self, user_id: int, months: int) -> Dict[str, Any]:
        """Get cost trends for the specified period."""
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=months * 30)
            
            # Get daily costs for trend analysis
            daily_costs = self.db.query(
                func.date(ContainerResourceUsage.snapshot_timestamp).label('date'),
                func.sum(ContainerResourceUsage.total_cost).label('daily_cost')
            ).join(AgentDeployment).join(Hiring).filter(
                and_(
                    Hiring.user_id == user_id,
                    ContainerResourceUsage.snapshot_timestamp >= start_date,
                    ContainerResourceUsage.snapshot_timestamp <= end_date
                )
            ).group_by(func.date(ContainerResourceUsage.snapshot_timestamp)).order_by(
                func.date(ContainerResourceUsage.snapshot_timestamp)
            ).all()
            
            # Calculate trends
            if len(daily_costs) >= 2:
                first_cost = daily_costs[0].daily_cost or 0
                last_cost = daily_costs[-1].daily_cost or 0
                
                if first_cost > 0:
                    cost_change_percent = ((last_cost - first_cost) / first_cost) * 100
                else:
                    cost_change_percent = 0
                
                # Calculate average daily cost
                total_cost = sum(d.daily_cost or 0 for d in daily_costs)
                avg_daily_cost = total_cost / len(daily_costs) if daily_costs else 0
                
                # Project monthly cost
                projected_monthly = avg_daily_cost * 30
                
                return {
                    "cost_change_percent": round(cost_change_percent, 2),
                    "trend": "increasing" if cost_change_percent > 5 else "decreasing" if cost_change_percent < -5 else "stable",
                    "average_daily_cost": round(avg_daily_cost, 6),
                    "projected_monthly_cost": round(projected_monthly, 6),
                    "daily_breakdown": [
                        {
                            "date": d.date.isoformat(),
                            "cost": round(d.daily_cost or 0, 6)
                        } for d in daily_costs
                    ]
                }
            else:
                return {
                    "cost_change_percent": 0.0,
                    "trend": "stable",
                    "average_daily_cost": 0.0,
                    "projected_monthly_cost": 0.0,
                    "daily_breakdown": []
                }
                
        except Exception as e:
            logger.error(f"Error getting cost trends: {e}")
            return {
                "cost_change_percent": 0.0,
                "trend": "stable",
                "average_daily_cost": 0.0,
                "projected_monthly_cost": 0.0,
                "daily_breakdown": []
            }
    
    async def get_deployment_cost_estimate(self, deployment_type: str, duration_hours: float, 
                                         avg_cpu_percent: float = 50.0, avg_memory_gb: float = 1.0) -> Dict[str, Any]:
        """Get cost estimate for a deployment before it starts."""
        try:
            estimate = self.resource_tracker.estimate_deployment_cost(
                deployment_type, duration_hours, avg_cpu_percent, avg_memory_gb
            )
            
            return {
                "deployment_type": deployment_type,
                "duration_hours": duration_hours,
                "estimated_costs": {
                    "cpu_cost": round(estimate["cpu_cost"], 6),
                    "memory_cost": round(estimate["memory_cost"], 6),
                    "storage_cost": round(estimate["storage_cost"], 6),
                    "total_cost": round(estimate["total_cost"], 6),
                    "cost_per_hour": round(estimate["cost_per_hour"], 6)
                },
                "assumptions": {
                    "avg_cpu_percent": avg_cpu_percent,
                    "avg_memory_gb": avg_memory_gb,
                    "pricing_model": "AWS-competitive hourly rates"
                },
                "currency": "USD"
            }
            
        except Exception as e:
            logger.error(f"Error getting deployment cost estimate: {e}")
            return {"error": f"Failed to get cost estimate: {str(e)}"}
    
    async def get_user_daily_usage(self, user_id: int, date: datetime) -> Dict[str, Any]:
        """Get detailed daily usage for a specific user and date."""
        try:
            daily_usage = self.resource_tracker.aggregate_daily_usage(user_id, date)
            
            if daily_usage:
                return {
                    "user_id": user_id,
                    "date": daily_usage["date"],
                    "summary": {
                        "total_cost": round(daily_usage["total_cost"], 6),
                        "total_cpu_hours": round(daily_usage["total_cpu_hours"], 4),
                        "total_memory_gb_hours": round(daily_usage["total_memory_gb_hours"], 4),
                        "total_network_gb": round(daily_usage["total_network_gb"], 4),
                        "total_requests": daily_usage["total_requests"]
                    },
                    "deployments": daily_usage["deployments"],
                    "hourly_breakdown": await self._get_hourly_breakdown(user_id, date),
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "user_id": user_id,
                    "date": date.date().isoformat(),
                    "summary": {
                        "total_cost": 0.0,
                        "total_cpu_hours": 0.0,
                        "total_memory_gb_hours": 0.0,
                        "total_network_gb": 0.0,
                        "total_requests": 0
                    },
                    "deployments": [],
                    "hourly_breakdown": [],
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting daily usage for user {user_id}: {e}")
            return {"error": f"Failed to get daily usage: {str(e)}"}
    
    async def _get_hourly_breakdown(self, user_id: int, date: datetime) -> List[Dict[str, Any]]:
        """Get hourly breakdown for a specific date."""
        try:
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            hourly_breakdown = []
            
            for hour in range(24):
                hour_start = date_start + timedelta(hours=hour)
                hour_end = hour_start + timedelta(hours=1)
                
                # Get all deployments active in this hour
                deployments = self.db.query(AgentDeployment).join(Hiring).filter(
                    and_(
                        Hiring.user_id == user_id,
                        AgentDeployment.created_at <= hour_end,
                        or_(
                            AgentDeployment.stopped_at.is_(None),
                            AgentDeployment.stopped_at > hour_start
                        )
                    )
                ).all()
                
                hour_total_cost = 0.0
                hour_total_cpu = 0.0
                hour_total_memory = 0.0
                hour_total_requests = 0
                
                for deployment in deployments:
                    # Get hourly usage for this deployment
                    hourly_usage = self.resource_tracker.calculate_hourly_usage(
                        deployment.deployment_id, hour_start
                    )
                    
                    if hourly_usage.get("snapshots_count", 0) > 0:
                        hour_total_cost += hourly_usage["total_cost"]
                        hour_total_cpu += hourly_usage["average_cpu_percent"]
                        hour_total_memory += hourly_usage["average_memory_gb"]
                
                # Get activity count for this hour
                hour_requests = self.db.query(AgentActivityLog).filter(
                    and_(
                        AgentActivityLog.user_id == user_id,
                        AgentActivityLog.activity_timestamp >= hour_start,
                        AgentActivityLog.activity_timestamp < hour_end
                    )
                ).count()
                
                hour_total_requests += hour_requests
                
                hourly_breakdown.append({
                    "hour": hour,
                    "time_range": f"{hour:02d}:00-{(hour+1):02d}:00",
                    "total_cost": round(hour_total_cost, 6),
                    "avg_cpu_percent": round(hour_total_cpu, 2),
                    "avg_memory_gb": round(hour_total_memory, 4),
                    "requests": hour_total_requests
                })
            
            return hourly_breakdown
            
        except Exception as e:
            logger.error(f"Error getting hourly breakdown: {e}")
            return []
    
    async def check_budget_limit(self, user_id: int, estimated_cost: float) -> Dict[str, Any]:
        """Check if user has sufficient budget for estimated costs."""
        try:
            budget = self.db.query(UserBudget).filter(UserBudget.user_id == user_id).first()
            
            if not budget:
                return {
                    "allowed": True,
                    "reason": "No budget configured",
                    "estimated_cost": estimated_cost
                }
            
            # Get current month's usage
            current_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_usage = self.resource_tracker.get_user_monthly_billing(
                user_id, current_month.year, current_month.month
            )
            
            current_monthly_cost = monthly_usage.get("total_cost", 0.0)
            projected_total = current_monthly_cost + estimated_cost
            
            if projected_total > budget.monthly_budget:
                return {
                    "allowed": False,
                    "reason": "Monthly budget would be exceeded",
                    "current_monthly_cost": round(current_monthly_cost, 6),
                    "monthly_budget": budget.monthly_budget,
                    "estimated_cost": estimated_cost,
                    "projected_total": round(projected_total, 6),
                    "remaining_budget": round(budget.monthly_budget - current_monthly_cost, 6)
                }
            
            return {
                "allowed": True,
                "reason": "Budget sufficient",
                "current_monthly_cost": round(current_monthly_cost, 6),
                "monthly_budget": budget.monthly_budget,
                "estimated_cost": estimated_cost,
                "remaining_budget": round(budget.monthly_budget - projected_total, 6)
            }
            
        except Exception as e:
            logger.error(f"Error checking budget limit: {e}")
            return {
                "allowed": True,
                "reason": "Error checking budget, allowing operation",
                "estimated_cost": estimated_cost
            }
