"""Earnings API endpoints for tracking user earnings from published agents."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db
from ..models.execution import Execution
from ..models.hiring import Hiring
from ..models.agent import Agent
from ..models.resource_usage import ExecutionResourceUsage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/earnings", tags=["earnings"])


@router.get("/summary")
async def get_earnings_summary(
    user_id: int = Query(..., description="User ID to get earnings for"),
    months: int = Query(12, description="Number of months to fetch"),
    db: Session = Depends(get_db)
):
    """Get earnings summary for the last N months for a specific user from their published agents."""
    try:
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=months * 30)
        
        # Initialize monthly data structure
        monthly_data = {}
        
        # Get all agents owned by this user
        user_agents = db.query(Agent).filter(Agent.owner_id == user_id).all()
        agent_ids = [agent.id for agent in user_agents]
        
        if not agent_ids:
            # User has no published agents
            return []
        
        # Get all hirings of this user's agents
        agent_hirings = db.query(Hiring).filter(
            and_(
                Hiring.created_at >= start_date,
                Hiring.created_at <= end_date,
                Hiring.agent_id.in_(agent_ids)
            )
        ).all()
        
        # Get all executions of this user's agents
        agent_executions = db.query(Execution).filter(
            and_(
                Execution.created_at >= start_date,
                Execution.created_at <= end_date,
                Execution.agent_id.in_(agent_ids)
            )
        ).all()
        
        # Process hirings to calculate earnings
        for hiring in agent_hirings:
            month_key = hiring.created_at.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_earnings": 0.0,
                    "total_hirings": 0,
                    "total_executions": 0,
                    "total_revenue": 0.0,
                    "total_resource_costs": 0.0,
                    "hirings": [],
                    "executions": []
                }
            
            # Get agent details
            agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
            agent_name = agent.name if agent else "Unknown Agent"
            
            # Count executions for this hiring
            hiring_executions = db.query(Execution).filter(
                Execution.hiring_id == hiring.id
            ).all()
            
            execution_count = len(hiring_executions)
            
            monthly_data[month_key]["total_hirings"] += 1
            monthly_data[month_key]["hirings"].append({
                "id": hiring.id,
                "agent_id": hiring.agent_id,
                "agent_name": agent_name,
                "status": hiring.status,
                "hired_at": hiring.created_at.isoformat(),
                "hired_by_user_id": hiring.user_id,
                "billing_cycle": hiring.billing_cycle or "monthly",
                "total_executions": execution_count,
                "agent_monthly_price": agent.monthly_price if agent else 0.0,
                "revenue": 0.0,  # Will be calculated
                "resource_costs": 0.0,  # Will be calculated
                "earnings": 0.0  # Will be calculated
            })
        
        # Process executions to calculate earnings
        for execution in agent_executions:
            month_key = execution.created_at.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_earnings": 0.0,
                    "total_hirings": 0,
                    "total_executions": 0,
                    "total_revenue": 0.0,
                    "total_resource_costs": 0.0,
                    "hirings": [],
                    "executions": []
                }
            
            # Get agent details
            agent = db.query(Agent).filter(Agent.id == execution.agent_id).first()
            agent_name = agent.name if agent else "Unknown Agent"
            
            monthly_data[month_key]["total_executions"] += 1
            monthly_data[month_key]["executions"].append({
                "id": execution.id,
                "execution_id": execution.execution_id,
                "hiring_id": execution.hiring_id,
                "agent_id": execution.agent_id,
                "agent_name": agent_name,
                "executed_at": execution.created_at.isoformat(),
                "status": execution.status,
                "execution_time": execution.duration_ms / 1000 if execution.duration_ms else None,
                "agent_price_per_use": agent.price_per_use if agent else 0.0,
                "revenue": 0.0,  # Will be calculated
                "resource_costs": 0.0,  # Will be calculated
                "earnings": 0.0,  # Will be calculated
                "resource_usage": []
            })
        
        # Calculate earnings for each month
        for month_data in monthly_data.values():
            month_earnings = 0.0
            month_revenue = 0.0
            month_resource_costs = 0.0
            
            # Calculate earnings from hirings (using agent's monthly_price if available)
            for hiring in month_data["hirings"]:
                # Get agent pricing information
                agent = db.query(Agent).filter(Agent.id == hiring["agent_id"]).first()
                if agent and agent.monthly_price:
                    hiring_revenue = agent.monthly_price
                else:
                    hiring_revenue = 0.0  # No monthly revenue if no monthly price set
                
                hiring["revenue"] = hiring_revenue
                month_revenue += hiring_revenue
                
                # Calculate resource costs for this hiring's executions
                hiring_resource_costs = 0.0
                for execution in month_data["executions"]:
                    if execution["hiring_id"] == hiring["id"]:
                        # Get resource usage for this execution
                        resource_usage = db.query(ExecutionResourceUsage).filter(
                            ExecutionResourceUsage.execution_id == execution["id"]
                        ).all()
                        
                        execution_resource_costs = sum(usage.cost for usage in resource_usage)
                        execution["resource_costs"] = execution_resource_costs
                        execution["resource_usage"] = [
                            {
                                "resource_type": usage.resource_type,
                                "provider": usage.resource_provider,
                                "model": usage.resource_model,
                                "operation_type": usage.operation_type,
                                "cost": usage.cost,
                                "input_tokens": usage.input_tokens,
                                "output_tokens": usage.output_tokens,
                                "duration_ms": usage.duration_ms,
                                "created_at": usage.created_at.isoformat() if usage.created_at else None
                            }
                            for usage in resource_usage
                        ]
                        
                        hiring_resource_costs += execution_resource_costs
                        month_resource_costs += execution_resource_costs
                
                hiring["resource_costs"] = hiring_resource_costs
                
                # Calculate earnings: 70% of (revenue - resource_costs)
                hiring_earnings = max(0, hiring_revenue - hiring_resource_costs) * 0.7
                hiring["earnings"] = hiring_earnings
                month_earnings += hiring_earnings
            
            # Calculate earnings from ALL executions (including those tied to hirings)
            for execution in month_data["executions"]:
                # Get agent pricing information
                agent = db.query(Agent).filter(Agent.id == execution["agent_id"]).first()
                
                # Calculate per-use revenue for ALL executions when price_per_use is set
                execution_revenue = 0.0
                if agent and agent.price_per_use:
                    execution_revenue = agent.price_per_use
                
                execution["revenue"] = execution_revenue
                month_revenue += execution_revenue
                
                # Get resource usage
                resource_usage = db.query(ExecutionResourceUsage).filter(
                    ExecutionResourceUsage.execution_id == execution["id"]
                ).all()
                
                execution_resource_costs = sum(usage.cost for usage in resource_usage)
                execution["resource_costs"] = execution_resource_costs
                execution["resource_usage"] = [
                    {
                        "resource_type": usage.resource_type,
                        "provider": usage.resource_provider,
                        "model": usage.resource_model,
                        "operation_type": usage.operation_type,
                        "cost": usage.cost,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "duration_ms": usage.duration_ms,
                        "created_at": usage.created_at.isoformat() if usage.created_at else None
                    }
                    for usage in resource_usage
                ]
                
                month_resource_costs += execution_resource_costs
                
                # Calculate earnings: 70% of (revenue - resource_costs)
                execution_earnings = max(0, execution_revenue - execution_resource_costs) * 0.7
                execution["earnings"] = execution_earnings
                month_earnings += execution_earnings
            
            # Update month totals
            month_data["total_earnings"] = month_earnings
            month_data["total_revenue"] = month_revenue
            month_data["total_resource_costs"] = month_resource_costs
        
        # Convert to list and sort by month
        result = list(monthly_data.values())
        result.sort(key=lambda x: x["month"], reverse=True)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching earnings summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch earnings summary: {str(e)}"
        )


@router.get("/agent/{agent_id}")
async def get_agent_earnings(
    agent_id: str,
    user_id: int = Query(..., description="User ID to verify ownership"),
    months: int = Query(12, description="Number of months to fetch"),
    db: Session = Depends(get_db)
):
    """Get earnings for a specific agent owned by the user."""
    try:
        # Verify agent ownership
        agent = db.query(Agent).filter(
            and_(
                Agent.id == agent_id,
                Agent.owner_id == user_id
            )
        ).first()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or access denied"
            )
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=months * 30)
        
        # Get hirings for this agent
        hirings = db.query(Hiring).filter(
            and_(
                Hiring.created_at >= start_date,
                Hiring.created_at <= end_date,
                Hiring.agent_id == agent_id
            )
        ).all()
        
        # Get executions for this agent
        executions = db.query(Execution).filter(
            and_(
                Execution.created_at >= start_date,
                Execution.created_at <= end_date,
                Execution.agent_id == agent_id
            )
        ).all()
        
        # Calculate earnings (similar logic to summary endpoint)
        total_earnings = 0.0
        total_revenue = 0.0
        total_resource_costs = 0.0
        
        # Process hirings
        for hiring in hirings:
            # Get agent pricing information
            agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
            if agent and agent.monthly_price:
                hiring_revenue = agent.monthly_price
            else:
                hiring_revenue = 0.0  # No monthly revenue if no monthly price set
            
            total_revenue += hiring_revenue
            
            # Get resource costs for this hiring
            hiring_executions = db.query(Execution).filter(
                Execution.hiring_id == hiring.id
            ).all()
            
            hiring_resource_costs = 0.0
            for execution in hiring_executions:
                resource_usage = db.query(ExecutionResourceUsage).filter(
                    ExecutionResourceUsage.execution_id == execution.id
                ).all()
                hiring_resource_costs += sum(usage.cost for usage in resource_usage)
            
            total_resource_costs += hiring_resource_costs
            
            # Calculate earnings: 70% of (revenue - resource_costs)
            hiring_earnings = max(0, hiring_revenue - hiring_resource_costs) * 0.7
            total_earnings += hiring_earnings
        
        # Process ALL executions (including those tied to hirings)
        for execution in executions:
            # Get agent pricing information
            agent = db.query(Agent).filter(Agent.id == execution.agent_id).first()
            
            # Calculate per-use revenue for ALL executions when price_per_use is set
            execution_revenue = 0.0
            if agent and agent.price_per_use:
                execution_revenue = agent.price_per_use
            
            total_revenue += execution_revenue
            
            # Get resource costs
            resource_usage = db.query(ExecutionResourceUsage).filter(
                ExecutionResourceUsage.execution_id == execution.id
            ).all()
            
            execution_resource_costs = sum(usage.cost for usage in resource_usage)
            total_resource_costs += execution_resource_costs
            
            # Calculate earnings: 70% of (revenue - resource_costs)
            execution_earnings = max(0, execution_revenue - execution_resource_costs) * 0.7
            total_earnings += execution_earnings
        
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "total_earnings": total_earnings,
            "total_revenue": total_revenue,
            "total_resource_costs": total_resource_costs,
            "platform_share": total_resource_costs,
            "user_share_percentage": 70.0,
            "period_months": months,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "hirings_count": len(hirings),
            "executions_count": len(executions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching agent earnings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent earnings: {str(e)}"
        )


@router.get("/stats")
async def get_earnings_stats(
    user_id: int = Query(..., description="User ID to get earnings stats for"),
    db: Session = Depends(get_db)
):
    """Get overall earnings statistics for a user."""
    try:
        # Get all agents owned by this user
        user_agents = db.query(Agent).filter(Agent.owner_id == user_id).all()
        agent_ids = [agent.id for agent in user_agents]
        
        if not agent_ids:
            return {
                "total_agents": 0,
                "total_earnings": 0.0,
                "total_revenue": 0.0,
                "total_resource_costs": 0.0,
                "average_earnings_per_agent": 0.0,
                "top_earning_agent": None,
                "monthly_trend": []
            }
        
        # Calculate total earnings across all agents
        total_earnings = 0.0
        total_revenue = 0.0
        total_resource_costs = 0.0
        agent_earnings = {}
        
        for agent in user_agents:
            # Get all hirings and executions for this agent
            agent_hirings = db.query(Hiring).filter(Hiring.agent_id == agent.id).all()
            agent_executions = db.query(Execution).filter(Execution.agent_id == agent.id).all()
            
            agent_revenue = 0.0
            agent_resource_costs = 0.0
            
            # Calculate revenue and costs for this agent
            for hiring in agent_hirings:
                # Get agent pricing information
                agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                if agent and agent.monthly_price:
                    agent_revenue += agent.monthly_price
                
                hiring_executions = db.query(Execution).filter(
                    Execution.hiring_id == hiring.id
                ).all()
                
                for execution in hiring_executions:
                    resource_usage = db.query(ExecutionResourceUsage).filter(
                        ExecutionResourceUsage.execution_id == execution.id
                    ).all()
                    agent_resource_costs += sum(usage.cost for usage in resource_usage)
            
            for execution in agent_executions:
                # Get agent pricing information
                agent = db.query(Agent).filter(Agent.id == execution.agent_id).first()
                if agent and agent.price_per_use:
                    agent_revenue += agent.price_per_use
                
                resource_usage = db.query(ExecutionResourceUsage).filter(
                    ExecutionResourceUsage.execution_id == execution.id
                ).all()
                agent_resource_costs += sum(usage.cost for usage in resource_usage)
            
            agent_earnings[agent.id] = {
                "name": agent.name,
                "revenue": agent_revenue,
                "resource_costs": agent_resource_costs,
                "earnings": max(0, agent_revenue - agent_resource_costs) * 0.7
            }
            
            total_revenue += agent_revenue
            total_resource_costs += agent_resource_costs
            total_earnings += agent_earnings[agent.id]["earnings"]
        
        # Find top earning agent
        top_earning_agent = None
        if agent_earnings:
            top_agent_id = max(agent_earnings.keys(), key=lambda k: agent_earnings[k]["earnings"])
            top_earning_agent = {
                "id": top_agent_id,
                "name": agent_earnings[top_agent_id]["name"],
                "earnings": agent_earnings[top_agent_id]["earnings"]
            }
        
        # Calculate monthly trend for the last 12 months
        monthly_trend = []
        for i in range(12):
            month_date = datetime.now(timezone.utc) - timedelta(days=30 * i)
            month_key = month_date.strftime("%Y-%m")
            
            # Get earnings for this month
            month_start = month_date.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            month_earnings = 0.0
            for agent_id in agent_ids:
                # Get hirings and executions for this month
                month_hirings = db.query(Hiring).filter(
                    and_(
                        Hiring.created_at >= month_start,
                        Hiring.created_at < month_end,
                        Hiring.agent_id == agent_id
                    )
                ).all()
                
                month_executions = db.query(Execution).filter(
                    and_(
                        Execution.created_at >= month_start,
                        Execution.created_at < month_end,
                        Execution.agent_id == agent_id
                    )
                ).all()
                
                # Calculate month earnings using actual agent pricing
                month_revenue = 0.0
                
                # Add revenue from hirings (monthly pricing)
                for hiring in month_hirings:
                    agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                    if agent and agent.monthly_price:
                        month_revenue += agent.monthly_price
                
                # Add revenue from ALL executions (per-use pricing)
                for execution in month_executions:
                    agent = db.query(Agent).filter(Agent.id == execution.agent_id).first()
                    if agent and agent.price_per_use:
                        month_revenue += agent.price_per_use
                
                month_earnings += month_revenue * 0.7  # 70% of revenue
            
            monthly_trend.append({
                "month": month_key,
                "earnings": month_earnings
            })
        
        monthly_trend.reverse()  # Oldest to newest
        
        return {
            "total_agents": len(user_agents),
            "total_earnings": total_earnings,
            "total_revenue": total_revenue,
            "total_resource_costs": total_resource_costs,
            "average_earnings_per_agent": total_earnings / len(user_agents) if user_agents else 0.0,
            "top_earning_agent": top_earning_agent,
            "monthly_trend": monthly_trend,
            "agent_breakdown": agent_earnings
        }
        
    except Exception as e:
        logger.error(f"Error fetching earnings stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch earnings stats: {str(e)}"
        )
