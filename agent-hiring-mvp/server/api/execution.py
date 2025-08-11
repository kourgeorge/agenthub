"""Execution API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database.config import get_session_dependency
from ..services.execution_service import ExecutionService, ExecutionCreateRequest
from ..models.execution import Execution, ExecutionStatus
from ..middleware.auth import get_current_user


class ExecutionRequest(BaseModel):
    hiring_id: int
    execution_type: str = "run"  # "initialize", "run", "cleanup"
    input_data: Optional[Dict[str, Any]] = None
    user_id: Optional[int] = None

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/", response_model=dict)
def create_execution(
    execution_data: ExecutionRequest,
    db: Session = Depends(get_session_dependency)
):
    """Create a new execution (initialize, run, or cleanup)."""
    execution_service = ExecutionService(db)
    
    try:
        # Validate execution type
        valid_types = ["initialize", "run", "cleanup"]
        if execution_data.execution_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid execution type. Must be one of: {valid_types}"
            )
        
        # For initialize type, check if agent requires initialization
        if execution_data.execution_type == "initialize":
            from ..services.hiring_service import HiringService
            hiring_service = HiringService(db)
            hiring = hiring_service.get_hiring(execution_data.hiring_id)
            
            if not hiring:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Hiring not found"
                )
            
            from ..models.agent import Agent
            agent = db.query(Agent).filter(Agent.id == hiring.agent_id).first()
            
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            # Check if agent requires initialization
            agent_config = execution_service._get_agent_config(agent)
            requires_initialization = agent_config.get('requires_initialization', False)
            
            if not requires_initialization:
                return {
                    "status": "success",
                    "message": "Agent does not require explicit initialization",
                    "initialization_skipped": True,
                    "hiring_id": execution_data.hiring_id,
                    "agent_id": hiring.agent_id
                }
        
        # Create execution
        execution = execution_service.create_execution(ExecutionCreateRequest(
            hiring_id=execution_data.hiring_id,
            user_id=execution_data.user_id,
            input_data=execution_data.input_data,
            execution_type=execution_data.execution_type
        ))
        
        return {
            "execution_id": execution.execution_id,
            "agent_id": execution.agent_id,
            "hiring_id": execution.hiring_id,
            "status": execution.status,
            "execution_type": execution.execution_type,
            "created_at": execution.created_at.isoformat(),
            "message": f"{execution_data.execution_type.capitalize()} execution created successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
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
        "container_logs": execution.container_logs,
        "created_at": execution.created_at.isoformat(),
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "duration_ms": execution.duration_ms,
    }


@router.post("/{execution_id}/run")
async def run_execution(execution_id: str, db: Session = Depends(get_session_dependency)):
    """Run an execution (initialize or run type)."""
    try:
        execution_service = ExecutionService(db)
        
        # Get execution to check its type
        execution = execution_service.get_execution(execution_id)
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        # Route based on execution type
        if execution.execution_type == "initialize":
            result = await execution_service.execute_initialization(execution_id)
        else:
            result = await execution_service.execute_agent(execution_id)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("error", "Execution failed")
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Execution failed for {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/agent/{agent_id}", response_model=List[dict])
def get_agent_executions(
    agent_id: str,
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


@router.get("/hiring/{hiring_id}", response_model=List[dict])
def get_hiring_executions(
    hiring_id: int,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get executions for a hiring."""
    execution_service = ExecutionService(db)
    executions = execution_service.get_hiring_executions(hiring_id, limit)
    
    # Get the hiring to check user ownership
    from ..models.hiring import Hiring
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
    
    return [
        {
            "execution_id": execution.execution_id,
            "agent_id": execution.agent_id,
            "status": execution.status,
            "execution_type": execution.execution_type,
            "input_data": execution.input_data,
            "output_data": execution.output_data,
            "error_message": execution.error_message,
            "container_logs": execution.container_logs,
            "created_at": execution.created_at.isoformat(),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
        }
        for execution in executions
    ]


@router.get("/stats/agent/{agent_id}")
def get_agent_execution_stats(agent_id: str, db: Session = Depends(get_session_dependency)):
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