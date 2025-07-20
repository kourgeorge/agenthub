"""Billing API endpoints for tracking costs and resource usage."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db
from ..models.execution import Execution
from ..models.hiring import Hiring
from ..models.agent import Agent
from ..models.resource_usage import ExecutionResourceUsage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/summary")
async def get_billing_summary(
    db: Session = Depends(get_db),
    months: int = Query(12, description="Number of months to fetch")
):
    """Get billing summary for the last N months."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # Initialize monthly data structure
        monthly_data = {}
        
        # Get executions
        executions = db.query(Execution).filter(
            and_(
                Execution.created_at >= start_date,
                Execution.created_at <= end_date
            )
        ).all()
        
        for execution in executions:
            month_key = execution.created_at.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_charges": 0.0,
                    "total_hirings": 0,
                    "total_executions": 0,
                    "hirings": [],
                    "executions": []
                }
            
            # Get agent name for this execution
            agent_name = "Unknown Agent"
            if execution.hiring_id:
                hiring = db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
                if hiring:
                    agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                    if agent:
                        agent_name = agent.name
            
            # Add execution data
            monthly_data[month_key]["total_executions"] += 1
            monthly_data[month_key]["executions"].append({
                "id": execution.id,
                "execution_id": execution.execution_id,  # Add the actual execution_id
                "hiring_id": execution.hiring_id,
                "agent_name": agent_name,  # Use the looked up agent name
                "executed_at": execution.created_at.isoformat(),
                "status": execution.status,
                "execution_time": execution.duration_ms / 1000 if execution.duration_ms else None,
                "charges": 0.0,  # Will be calculated from resource usage
                "resource_usage": []
            })
        
        # Get hiring data
        hirings = db.query(Hiring).filter(
            and_(
                Hiring.created_at >= start_date,
                Hiring.created_at <= end_date
            )
        ).all()
        
        for hiring in hirings:
            month_key = hiring.created_at.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "total_charges": 0.0,
                    "total_hirings": 0,
                    "total_executions": 0,
                    "hirings": [],
                    "executions": []
                }
            
            # Get agent name
            agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
            agent_name = agent.name if agent else "Unknown Agent"
            
            # Count executions for this hiring
            execution_count = db.query(Execution).filter(
                Execution.hiring_id == hiring.id
            ).count()
            
            monthly_data[month_key]["total_hirings"] += 1
            monthly_data[month_key]["hirings"].append({
                "id": hiring.id,
                "agent_id": hiring.agent_id,
                "agent_name": agent_name,
                "status": hiring.status,
                "hired_at": hiring.created_at.isoformat(),
                "billing_cycle": "monthly",  # Default for now
                "total_executions": execution_count,
                "charges": 0.0  # Will be calculated from resource usage
            })
        
        # Get resource usage data and calculate charges
        resource_usage = db.query(ExecutionResourceUsage).filter(
            and_(
                ExecutionResourceUsage.created_at >= start_date,
                ExecutionResourceUsage.created_at <= end_date
            )
        ).all()
        
        # Calculate charges from resource usage
        for usage in resource_usage:
            # Find the execution this usage belongs to
            for month_data in monthly_data.values():
                for execution in month_data["executions"]:
                    if str(execution["id"]) == str(usage.execution_id):
                        execution["charges"] += usage.cost
                        execution["resource_usage"].append({
                            "resource_type": usage.resource_type,
                            "provider": usage.resource_provider,
                            "model": usage.resource_model,
                            "operation_type": usage.operation_type,
                            "cost": usage.cost,
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                            "duration_ms": usage.duration_ms,
                            "created_at": usage.created_at.isoformat() if usage.created_at else None
                        })
                        break
        
        # Calculate total charges for each month
        for month_data in monthly_data.values():
            # Sum execution charges
            month_data["total_charges"] = sum(
                execution["charges"] for execution in month_data["executions"]
            )
            
            # Calculate hiring charges (for now, just sum execution charges)
            for hiring in month_data["hirings"]:
                hiring["charges"] = sum(
                    execution["charges"] for execution in month_data["executions"]
                    if execution["hiring_id"] == hiring["id"]
                )
        
        # Convert to list and sort by month
        result = list(monthly_data.values())
        result.sort(key=lambda x: x["month"], reverse=True)
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching billing summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch billing summary: {str(e)}"
        )


@router.get("/execution/{execution_id}/resources")
async def get_execution_resources(
    execution_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed resource usage for a specific execution."""
    try:
        # Try to find execution by execution_id string first
        execution = db.query(Execution).filter(Execution.execution_id == execution_id).first()
        
        # If not found by execution_id, try by integer id
        if not execution:
            try:
                execution_id_int = int(execution_id)
                execution = db.query(Execution).filter(Execution.id == execution_id_int).first()
            except ValueError:
                pass
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        # Get resource usage for this execution (using the integer id)
        resource_usage = db.query(ExecutionResourceUsage).filter(
            ExecutionResourceUsage.execution_id == execution.id
        ).all()
        
        # Get agent name
        agent_name = "Unknown Agent"
        if execution.hiring_id:
            hiring = db.query(Hiring).filter(Hiring.id == execution.hiring_id).first()
            if hiring:
                agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                if agent:
                    agent_name = agent.name
        
        # Format resource usage data
        resources = []
        total_cost = 0.0
        
        for usage in resource_usage:
            resources.append({
                "id": usage.id,
                "resource_type": usage.resource_type,
                "provider": usage.resource_provider,
                "model": usage.resource_model,
                "operation_type": usage.operation_type,
                "cost": usage.cost,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "duration_ms": usage.duration_ms,
                "request_metadata": usage.request_metadata,
                "response_metadata": usage.response_metadata,
                "created_at": usage.created_at.isoformat() if usage.created_at else None
            })
            total_cost += usage.cost
        
        return {
            "execution_id": execution.execution_id,  # Return the actual execution_id string
            "agent_name": agent_name,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
            "total_cost": total_cost,
            "resource_count": len(resources),
            "resources": resources
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching execution resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch execution resources: {str(e)}"
        )


@router.get("/invoice/{month}")
async def download_invoice(
    month: str,
    db: Session = Depends(get_db)
):
    """Download invoice for a specific month (placeholder)."""
    # This would generate a PDF invoice in production
    # For now, return a simple JSON response
    return {
        "message": f"Invoice for {month}",
        "status": "not_implemented",
        "note": "PDF generation not implemented yet"
    } 