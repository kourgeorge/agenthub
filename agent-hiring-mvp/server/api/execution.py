"""Execution API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.config import get_session_dependency
from ..services.execution_service import ExecutionService, ExecutionCreateRequest
from ..models.execution import Execution, ExecutionStatus

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/", response_model=dict)
def create_execution(
    execution_data: ExecutionCreateRequest,
    db: Session = Depends(get_session_dependency)
):
    """Create a new execution."""
    execution_service = ExecutionService(db)
    
    try:
        execution = execution_service.create_execution(execution_data)
        
        return {
            "execution_id": execution.execution_id,
            "agent_id": execution.agent_id,
            "hiring_id": execution.hiring_id,
            "status": execution.status,
            "created_at": execution.created_at.isoformat(),
            "message": "Execution created successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{execution_id}", response_model=dict)
def get_execution(execution_id: str, db: Session = Depends(get_session_dependency)):
    """Get an execution by ID."""
    execution_service = ExecutionService(db)
    execution = execution_service.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {
        "execution_id": execution.execution_id,
        "agent_id": execution.agent_id,
        "hiring_id": execution.hiring_id,
        "user_id": execution.user_id,
        "status": execution.status,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "error_message": execution.error_message,
        "created_at": execution.created_at.isoformat(),
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "duration_ms": execution.duration_ms,
    }


@router.post("/{execution_id}/run")
def run_execution(execution_id: str, db: Session = Depends(get_session_dependency)):
    """Run an execution."""
    execution_service = ExecutionService(db)
    result = execution_service.execute_agent(execution_id)
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Execution failed")
        )
    
    return result


@router.get("/agent/{agent_id}", response_model=List[dict])
def get_agent_executions(
    agent_id: int,
    limit: int = 100,
    db: Session = Depends(get_session_dependency)
):
    """Get executions for an agent."""
    execution_service = ExecutionService(db)
    executions = execution_service.get_agent_executions(agent_id, limit)
    
    return [
        {
            "execution_id": execution.execution_id,
            "status": execution.status,
            "created_at": execution.created_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
        }
        for execution in executions
    ]


@router.get("/user/{user_id}", response_model=List[dict])
def get_user_executions(
    user_id: int,
    limit: int = 100,
    db: Session = Depends(get_session_dependency)
):
    """Get executions for a user."""
    execution_service = ExecutionService(db)
    executions = execution_service.get_user_executions(user_id, limit)
    
    return [
        {
            "execution_id": execution.execution_id,
            "agent_id": execution.agent_id,
            "status": execution.status,
            "created_at": execution.created_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
        }
        for execution in executions
    ]


@router.get("/stats/agent/{agent_id}")
def get_agent_execution_stats(agent_id: int, db: Session = Depends(get_session_dependency)):
    """Get execution statistics for an agent."""
    execution_service = ExecutionService(db)
    stats = execution_service.get_execution_stats(agent_id=agent_id)
    
    return stats


@router.get("/stats/user/{user_id}")
def get_user_execution_stats(user_id: int, db: Session = Depends(get_session_dependency)):
    """Get execution statistics for a user."""
    execution_service = ExecutionService(db)
    stats = execution_service.get_execution_stats(user_id=user_id)
    
    return stats


@router.put("/{execution_id}/status")
def update_execution_status(
    execution_id: str,
    status: str,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    db: Session = Depends(get_session_dependency)
):
    """Update execution status."""
    execution_service = ExecutionService(db)
    
    try:
        execution_status = ExecutionStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status}"
        )
    
    execution = execution_service.update_execution_status(
        execution_id, execution_status, output_data, error_message
    )
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {
        "execution_id": execution.execution_id,
        "status": execution.status,
        "message": "Execution status updated successfully"
    } 