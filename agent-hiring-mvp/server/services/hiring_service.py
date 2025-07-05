"""Hiring service for managing agent hiring workflow."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..models.hiring import Hiring, HiringStatus
from ..models.agent import Agent
from ..models.user import User

logger = logging.getLogger(__name__)


class HiringCreateRequest(BaseModel):
    """Request model for creating a hiring."""
    agent_id: int
    user_id: int
    requirements: Optional[Dict[str, Any]] = None
    budget: Optional[float] = None
    duration_hours: Optional[int] = None


class HiringService:
    """Service for managing agent hiring workflow."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_hiring(self, hiring_data: HiringCreateRequest) -> Hiring:
        """Create a new hiring record."""
        hiring = Hiring(
            agent_id=hiring_data.agent_id,
            user_id=hiring_data.user_id,
            status=HiringStatus.ACTIVE.value,
            config=hiring_data.requirements or {},
            hired_at=datetime.utcnow(),
        )
        
        self.db.add(hiring)
        self.db.commit()
        self.db.refresh(hiring)
        
        logger.info(f"Created hiring: {hiring.id} for agent {hiring_data.agent_id}")
        return hiring
    
    def get_hiring(self, hiring_id: int) -> Optional[Hiring]:
        """Get a hiring by ID."""
        return self.db.query(Hiring).filter(Hiring.id == hiring_id).first()
    
    def update_hiring_status(self, hiring_id: int, status: HiringStatus, 
                           notes: Optional[str] = None) -> Optional[Hiring]:
        """Update hiring status."""
        hiring = self.get_hiring(hiring_id)
        if not hiring:
            return None
        
        hiring.status = status.value
        
        if status == HiringStatus.ACTIVE:
            hiring.hired_at = datetime.utcnow()
        elif status == HiringStatus.SUSPENDED:
            # Update last_executed_at as a proxy for updated_at
            hiring.last_executed_at = datetime.utcnow()
        elif status == HiringStatus.CANCELLED:
            # Update last_executed_at as a proxy for updated_at
            hiring.last_executed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(hiring)
        
        logger.info(f"Updated hiring {hiring_id} status to {status.value}")
        return hiring
    
    def get_user_hirings(self, user_id: int, status: Optional[HiringStatus] = None) -> List[Hiring]:
        """Get hirings for a user."""
        query = self.db.query(Hiring).filter(Hiring.user_id == user_id)
        
        if status:
            query = query.filter(Hiring.status == status.value)
        
        return query.order_by(Hiring.created_at.desc()).all()
    
    def get_agent_hirings(self, agent_id: int, status: Optional[HiringStatus] = None) -> List[Hiring]:
        """Get hirings for an agent."""
        query = self.db.query(Hiring).filter(Hiring.agent_id == agent_id)
        
        if status:
            query = query.filter(Hiring.status == status.value)
        
        return query.order_by(Hiring.created_at.desc()).all()
    
    def activate_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Activate a hiring."""
        return self.update_hiring_status(hiring_id, HiringStatus.ACTIVE, notes)
    
    def suspend_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Suspend a hiring."""
        return self.update_hiring_status(hiring_id, HiringStatus.SUSPENDED, notes)
    
    def cancel_hiring(self, hiring_id: int, notes: Optional[str] = None) -> Optional[Hiring]:
        """Cancel a hiring."""
        return self.update_hiring_status(hiring_id, HiringStatus.CANCELLED, notes)
    
    def get_hiring_stats(self, user_id: Optional[int] = None, agent_id: Optional[int] = None) -> Dict[str, Any]:
        """Get hiring statistics."""
        query = self.db.query(Hiring)
        
        if user_id:
            query = query.filter(Hiring.user_id == user_id)
        
        if agent_id:
            query = query.filter(Hiring.agent_id == agent_id)
        
        total_hirings = query.count()
        active_hirings = query.filter(Hiring.status == HiringStatus.ACTIVE.value).count()
        suspended_hirings = query.filter(Hiring.status == HiringStatus.SUSPENDED.value).count()
        cancelled_hirings = query.filter(Hiring.status == HiringStatus.CANCELLED.value).count()
        expired_hirings = query.filter(Hiring.status == HiringStatus.EXPIRED.value).count()
        
        return {
            "total_hirings": total_hirings,
            "active_hirings": active_hirings,
            "suspended_hirings": suspended_hirings,
            "cancelled_hirings": cancelled_hirings,
            "expired_hirings": expired_hirings,
            "active_rate": (active_hirings / total_hirings * 100) if total_hirings > 0 else 0,
        }
    
    def get_active_hirings(self) -> List[Hiring]:
        """Get all active hiring requests."""
        return (
            self.db.query(Hiring)
            .filter(Hiring.status == HiringStatus.ACTIVE.value)
            .order_by(Hiring.hired_at.asc())
            .all()
        )
    
    def get_hiring_with_details(self, hiring_id: int) -> Optional[Dict[str, Any]]:
        """Get hiring with agent and user details."""
        hiring = (
            self.db.query(Hiring)
            .join(Agent, Hiring.agent_id == Agent.id)
            .join(User, Hiring.user_id == User.id)
            .filter(Hiring.id == hiring_id)
            .first()
        )
        
        if not hiring:
            return None
        
        return {
            "id": hiring.id,
            "status": hiring.status,
            "config": hiring.config,
            "hired_at": hiring.hired_at.isoformat(),
            "expires_at": hiring.expires_at.isoformat() if hiring.expires_at else None,
            "total_executions": hiring.total_executions,
            "last_executed_at": hiring.last_executed_at.isoformat() if hiring.last_executed_at else None,
            "billing_cycle": hiring.billing_cycle,
            "next_billing_date": hiring.next_billing_date.isoformat() if hiring.next_billing_date else None,
            "agent": {
                "id": hiring.agent.id,
                "name": hiring.agent.name,
                "description": hiring.agent.description,
                "creator_id": hiring.agent.creator_id,
            },
            "user": {
                "id": hiring.user.id,
                "username": hiring.user.username,
                "email": hiring.user.email,
            }
        } 