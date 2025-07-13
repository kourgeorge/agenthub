"""Billing API endpoints."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from ..database.config import get_session_dependency
from ..models.hiring import Hiring, HiringStatus
from ..models.execution import Execution
from ..models.agent import Agent

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/summary")
def get_billing_summary(
    user_id: Optional[int] = 1,  # Default to user 1 for now
    months: int = 12,
    db: Session = Depends(get_session_dependency)
):
    """Get billing summary for the last N months."""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        billing_data = []
        
        # Generate data for each month
        current_date = start_date.replace(day=1)
        while current_date <= end_date:
            month_key = current_date.strftime("%Y-%m")
            next_month = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            
            # Get hirings for this month
            hirings = db.query(Hiring).filter(
                Hiring.user_id == user_id,
                Hiring.hired_at >= current_date,
                Hiring.hired_at < next_month
            ).all()
            
            # Get executions for this month
            executions = db.query(Execution).join(Hiring).filter(
                Hiring.user_id == user_id,
                Execution.started_at >= current_date,
                Execution.started_at < next_month
            ).all()
            
            # Calculate charges (simplified pricing model)
            hiring_charges = sum(calculate_hiring_charges(hiring) for hiring in hirings)
            execution_charges = sum(calculate_execution_charges(execution) for execution in executions)
            total_charges = hiring_charges + execution_charges
            
            # Prepare hiring data
            hiring_data = []
            for hiring in hirings:
                agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
                hiring_data.append({
                    "id": hiring.id,
                    "agent_id": hiring.agent_id,
                    "agent_name": agent.name if agent else f"Agent {hiring.agent_id}",
                    "status": hiring.status,
                    "hired_at": hiring.hired_at.isoformat(),
                    "billing_cycle": hiring.billing_cycle or "per_use",
                    "total_executions": hiring.total_executions,
                    "charges": calculate_hiring_charges(hiring)
                })
            
            # Prepare execution data
            execution_data = []
            for execution in executions:
                agent = db.query(Agent).filter(Agent.id == execution.hiring.agent_id).first()
                execution_data.append({
                    "id": execution.id,
                    "hiring_id": execution.hiring_id,
                    "agent_name": agent.name if agent else f"Agent {execution.hiring.agent_id}",
                    "executed_at": execution.started_at.isoformat() if execution.started_at else None,
                    "status": execution.status,
                    "execution_time": execution.duration_ms / 1000 if execution.duration_ms else None,
                    "charges": calculate_execution_charges(execution)
                })
            
            billing_data.append({
                "month": month_key,
                "total_charges": total_charges,
                "total_hirings": len(hirings),
                "total_executions": len(executions),
                "hirings": hiring_data,
                "executions": execution_data
            })
            
            current_date = next_month
        
        return billing_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating billing summary: {str(e)}"
        )


@router.get("/invoice/{month}")
def download_invoice(
    month: str,
    user_id: Optional[int] = 1,  # Default to user 1 for now
    db: Session = Depends(get_session_dependency)
):
    """Download invoice for a specific month."""
    try:
        # Parse month
        month_date = datetime.strptime(month, "%Y-%m")
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        # Get billing data for the month
        hirings = db.query(Hiring).filter(
            Hiring.user_id == user_id,
            Hiring.hired_at >= month_date,
            Hiring.hired_at < next_month
        ).all()
        
        executions = db.query(Execution).join(Hiring).filter(
            Hiring.user_id == user_id,
            Execution.started_at >= month_date,
            Execution.started_at < next_month
        ).all()
        
        # Calculate totals
        hiring_charges = sum(calculate_hiring_charges(hiring) for hiring in hirings)
        execution_charges = sum(calculate_execution_charges(execution) for execution in executions)
        total_charges = hiring_charges + execution_charges
        
        # For now, return a simple JSON response
        # In a real implementation, you would generate a PDF invoice
        invoice_data = {
            "invoice_number": f"INV-{month}-{user_id}",
            "month": month,
            "user_id": user_id,
            "issue_date": datetime.utcnow().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
            "total_charges": total_charges,
            "hiring_charges": hiring_charges,
            "execution_charges": execution_charges,
            "total_hirings": len(hirings),
            "total_executions": len(executions),
            "currency": "USD"
        }
        
        return invoice_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating invoice: {str(e)}"
        )


def calculate_hiring_charges(hiring: Hiring) -> float:
    """Calculate charges for a hiring based on billing cycle."""
    # Simplified pricing model
    base_hiring_cost = 5.0  # $5 base cost per hiring
    
    if hiring.billing_cycle == "monthly":
        return base_hiring_cost * 30  # $150 for monthly
    elif hiring.billing_cycle == "lifetime":
        return base_hiring_cost * 365  # $1825 for lifetime
    else:  # per_use
        return base_hiring_cost  # $5 for per-use


def calculate_execution_charges(execution: Execution) -> float:
    """Calculate charges for an execution."""
    # Simplified pricing model
    base_execution_cost = 0.10  # $0.10 per execution
    
    # Add time-based cost if duration_ms is available
    time_cost = 0
    if execution.duration_ms:
        time_cost = (execution.duration_ms / 1000 / 60) * 0.05  # $0.05 per minute
    
    return base_execution_cost + time_cost 