"""Users API router."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database.config import get_session_dependency
from ..models.user import User

router = APIRouter(tags=["users"])


@router.get("/users", response_model=List[dict])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_session_dependency)
):
    """Get all users with pagination."""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        for user in users
    ]


@router.get("/users/{user_id}", response_model=dict)
def get_user(
    user_id: int,
    db: Session = Depends(get_session_dependency)
):
    """Get a specific user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "preferences": user.preferences,
    }


@router.get("/users/username/{username}", response_model=dict)
def get_user_by_username(
    username: str,
    db: Session = Depends(get_session_dependency)
):
    """Get a user by username."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "preferences": user.preferences,
    }


@router.get("/users/stats")
def get_user_stats(db: Session = Depends(get_session_dependency)):
    """Get user statistics."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
    } 