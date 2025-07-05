"""Hiring API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.config import get_session_dependency
from ..services.hiring_service import HiringService, HiringCreateRequest
from ..models.hiring import Hiring, HiringStatus

router = APIRouter(prefix="/hiring", tags=["hiring"])


@router.post("/", response_model=dict)
def create_hiring(
    hiring_data: HiringCreateRequest,
    db: Session = Depends(get_session_dependency)
):
    """Create a new hiring request."""
    hiring_service = HiringService(db)
    hiring = hiring_service.create_hiring(hiring_data)
    
    return {
        "id": hiring.id,
        "agent_id": hiring.agent_id,
        "user_id": hiring.user_id,
        "status": hiring.status,
        "hired_at": hiring.hired_at.isoformat(),
        "message": "Hiring created successfully"
    }


@router.get("/{hiring_id}", response_model=dict)
def get_hiring(hiring_id: int, db: Session = Depends(get_session_dependency)):
    """Get a hiring by ID."""
    hiring_service = HiringService(db)
    hiring = hiring_service.get_hiring(hiring_id)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    return {
        "id": hiring.id,
        "agent_id": hiring.agent_id,
        "user_id": hiring.user_id,
        "status": hiring.status,
        "hired_at": hiring.hired_at.isoformat(),
        "expires_at": hiring.expires_at.isoformat() if hiring.expires_at else None,
        "config": hiring.config,
        "total_executions": hiring.total_executions,
        "last_executed_at": hiring.last_executed_at.isoformat() if hiring.last_executed_at else None,
    }


@router.get("/user/{user_id}", response_model=List[dict])
def get_user_hirings(
    user_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_session_dependency)
):
    """Get all hirings for a user."""
    hiring_service = HiringService(db)
    
    if status:
        try:
            hiring_status = HiringStatus(status)
            hirings = hiring_service.get_user_hirings(user_id, hiring_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    else:
        hirings = hiring_service.get_user_hirings(user_id)
    
    return [
        {
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": hiring.total_executions,
        }
        for hiring in hirings
    ]


@router.get("/agent/{agent_id}", response_model=List[dict])
def get_agent_hirings(
    agent_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_session_dependency)
):
    """Get all hirings for an agent."""
    hiring_service = HiringService(db)
    
    if status:
        try:
            hiring_status = HiringStatus(status)
            hirings = hiring_service.get_agent_hirings(agent_id, hiring_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )
    else:
        hirings = hiring_service.get_agent_hirings(agent_id)
    
    return [
        {
            "id": hiring.id,
            "user_id": hiring.user_id,
            "status": hiring.status,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": hiring.total_executions,
        }
        for hiring in hirings
    ]


@router.put("/{hiring_id}/activate")
def activate_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_session_dependency)
):
    """Activate a hiring."""
    hiring_service = HiringService(db)
    hiring = hiring_service.activate_hiring(hiring_id, notes)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    return {
        "id": hiring.id,
        "status": hiring.status,
        "message": "Hiring activated successfully"
    }


@router.put("/{hiring_id}/suspend")
def suspend_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_session_dependency)
):
    """Suspend a hiring."""
    hiring_service = HiringService(db)
    hiring = hiring_service.suspend_hiring(hiring_id, notes)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    return {
        "id": hiring.id,
        "status": hiring.status,
        "message": "Hiring suspended successfully"
    }


@router.put("/{hiring_id}/cancel")
def cancel_hiring(
    hiring_id: int,
    notes: Optional[str] = None,
    db: Session = Depends(get_session_dependency)
):
    """Cancel a hiring."""
    hiring_service = HiringService(db)
    hiring = hiring_service.cancel_hiring(hiring_id, notes)
    
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    return {
        "id": hiring.id,
        "status": hiring.status,
        "message": "Hiring cancelled successfully"
    }


@router.get("/stats/user/{user_id}")
def get_user_hiring_stats(user_id: int, db: Session = Depends(get_session_dependency)):
    """Get hiring statistics for a user."""
    hiring_service = HiringService(db)
    stats = hiring_service.get_hiring_stats(user_id=user_id)
    
    return stats


@router.get("/stats/agent/{agent_id}")
def get_agent_hiring_stats(agent_id: int, db: Session = Depends(get_session_dependency)):
    """Get hiring statistics for an agent."""
    hiring_service = HiringService(db)
    stats = hiring_service.get_hiring_stats(agent_id=agent_id)
    
    return stats


@router.get("/active/list")
def get_active_hirings(db: Session = Depends(get_session_dependency)):
    """Get all active hirings."""
    hiring_service = HiringService(db)
    hirings = hiring_service.get_active_hirings()
    
    return [
        {
            "id": hiring.id,
            "agent_id": hiring.agent_id,
            "user_id": hiring.user_id,
            "hired_at": hiring.hired_at.isoformat(),
            "total_executions": hiring.total_executions,
        }
        for hiring in hirings
    ] 