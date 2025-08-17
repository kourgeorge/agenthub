"""Execution API endpoints."""

import asyncio
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

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/", response_model=dict)
def create_execution(
    execution_data: ExecutionRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Create a new execution (initialize, run, or cleanup)."""
    try:
        # Create execution service with its own database session
        execution_service = ExecutionService()  # No db parameter = creates own session
        
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
        
        # Get the hiring to validate ownership and get user_id if not provided
        from ..models.hiring import Hiring
        hiring = db.query(Hiring).filter(Hiring.id == execution_data.hiring_id).first()
        if not hiring:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hiring not found"
            )
        
        # Ensure the user can only execute their own hirings
        if hiring.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only execute your own hirings"
            )
        
        # Use the authenticated user's ID, with fallback to hiring user_id
        user_id = current_user.id or hiring.user_id
        
        # Create execution
        execution = execution_service.create_execution(ExecutionCreateRequest(
            hiring_id=execution_data.hiring_id,
            user_id=user_id,
            input_data=execution_data.input_data,
            execution_type=execution_data.execution_type
        ))
        
        return {
            "execution_id": execution.execution_id,
            "agent_id": execution.agent_id,
            "hiring_id": execution.hiring_id,
            "status": execution.status,
            "execution_type": execution_data.execution_type,
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
def get_execution(
    execution_id: str, 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get an execution by ID."""
    import logging
    logger = logging.getLogger(__name__)
    
    execution_service = ExecutionService(db)
    execution = execution_service.get_execution(execution_id)
    
    if not execution:
        logger.warning(f"Execution not found: {execution_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    # Ensure the user can only access their own executions
    if execution.user_id != current_user.id:
        logger.warning(f"Access denied: {execution_id} for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own executions"
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
async def run_execution(
    execution_id: str, 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Run an execution (initialize or run type) and wait for completion."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Create execution service with its own database session
        # This prevents the session from being closed when the API request ends
        execution_service = ExecutionService()  # No db parameter = creates own session
        
        # Get execution to check its type and ownership
        execution = execution_service.get_execution(execution_id)
        if not execution:
            logger.warning(f"Execution not found: {execution_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Execution not found"
            )
        
        # Ensure the user can only run their own executions
        if execution.user_id != current_user.id:
            logger.warning(f"Access denied: {execution_id} for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only run your own executions"
            )
        
        # Update execution status to running immediately
        execution_service.update_execution_status(execution_id, ExecutionStatus.RUNNING)
        logger.info(f"🚀 Execution {execution_id} status set to RUNNING")

        # Start execution in background (non-blocking)
        try:
            logger.info(f"🚀 Starting execution for {execution_id} in background")

            # Create background task for execution
            if execution.execution_type == "initialize":
                logger.info(f"Starting initialization for execution {execution_id}")
                asyncio.create_task(execution_service.execute_initialization(execution_id, user_id=current_user.id))
            else:
                logger.info(f"Starting agent execution for execution {execution_id}")
                asyncio.create_task(execution_service.execute_agent(execution_id, user_id=current_user.id))

            # Return immediately - execution is running in background
            return {
                "status": "started",
                "execution_id": execution_id,
                "message": f"{execution.execution_type.capitalize()} execution started successfully",
                "execution_type": execution.execution_type
            }

        except Exception as e:
            logger.error(f"Failed to start execution for {execution_id}: {e}")
            # Update status to failed
            try:
                execution_service.update_execution_status(execution_id, ExecutionStatus.FAILED, error_message=str(e))
                logger.error(f"Execution {execution_id} status set to FAILED due to error: {str(e)}")
            except Exception as update_error:
                logger.error(f"Failed to update execution status for {execution_id}: {update_error}")
            
            # Return error response instead of raising exception
            return {
                "status": "error",
                "execution_id": execution_id,
                "error": f"Failed to start execution: {str(e)}",
                "execution_type": execution.execution_type
            }

    except HTTPException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Execution failed for {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/agent/{agent_id}", response_model=List[dict])
async def get_agent_executions(
    agent_id: str,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get executions for an agent."""
    execution_service = ExecutionService(db)
    executions = execution_service.get_agent_executions(agent_id, limit)
    
    # Filter to only show user's own executions for this agent
    user_executions = [execution for execution in executions if execution.user_id == current_user.id]
    
    return [
        {
            "execution_id": execution.execution_id,
            "status": execution.status,
            "created_at": execution.created_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
        }
        for execution in user_executions
    ]


@router.get("/user/{user_id}", response_model=List[dict])
async def get_user_executions(
    user_id: int,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get executions for a user."""
    # Ensure the user can only access their own executions
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own executions"
        )
    
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
async def get_hiring_executions(
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
def get_agent_execution_stats(
    agent_id: str, 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get execution statistics for an agent."""
    execution_service = ExecutionService(db)
    stats = execution_service.get_execution_stats(agent_id=agent_id, user_id=current_user.id)
    
    return stats


@router.get("/stats/user/{user_id}")
def get_user_execution_stats(
    user_id: int, 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get execution statistics for a user."""
    # Ensure the user can only access their own stats
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own statistics"
        )
    
    execution_service = ExecutionService(db)
    stats = execution_service.get_execution_stats(user_id=user_id)
    
    return stats


@router.get("/stats/global")
def get_global_execution_stats(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Get global execution statistics for the entire system."""
    # For now, only allow global stats for admin users
    # In the future, this could be expanded to show system-wide metrics
    if not current_user.is_active:  # Basic check - could add admin role check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Insufficient permissions for global statistics"
        )
    
    execution_service = ExecutionService(db)
    stats = execution_service.get_execution_stats()  # No filters = global stats
    
    return stats


@router.put("/{execution_id}/status")
def update_execution_status(
    execution_id: str,
    status: str,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_session_dependency)
):
    """Update execution status."""
    execution_service = ExecutionService(db)
    
    # Get the execution to check ownership
    execution = execution_service.get_execution(execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    # Ensure the user can only update their own executions
    if execution.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update your own executions"
        )
    
    try:
        execution_status = ExecutionStatus(status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {status}"
        )
    
    updated_execution = execution_service.update_execution_status(
        execution_id, execution_status, output_data, error_message
    )
    
    if not updated_execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    return {
        "execution_id": updated_execution.execution_id,
        "status": updated_execution.status,
        "message": "Execution status updated successfully"
    } 