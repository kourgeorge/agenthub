"""Statistics API endpoints for system-wide metrics."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models.hiring import Hiring
from ..models.execution import Execution
from ..models.agent import Agent
from ..models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/system")
def get_system_stats(db: Session = Depends(get_db)):
    """Get system-wide statistics for the entire platform."""
    try:
        # Get total hirings (all states including suspended and deleted)
        total_hirings = db.query(Hiring).count()
        
        # Get total executions
        total_executions = db.query(Execution).count()
        
        # Get total agents
        total_agents = db.query(Agent).count()
        
        # Get total users
        total_users = db.query(User).count()
        
        # Get active hirings (currently active)
        active_hirings = db.query(Hiring).filter(Hiring.status == "active").count()
        
        # Get completed executions
        completed_executions = db.query(Execution).filter(Execution.status == "completed").count()
        
        return {
            "total_hirings": total_hirings,
            "total_executions": total_executions,
            "total_agents": total_agents,
            "total_users": total_users,
            "active_hirings": active_hirings,
            "completed_executions": completed_executions,
            "success_rate": (completed_executions / total_executions * 100) if total_executions > 0 else 0,
        }
        
    except Exception as e:
        logger.error(f"Error fetching system statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch system statistics: {str(e)}"
        )
