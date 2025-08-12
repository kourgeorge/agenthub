"""Authentication middleware for FastAPI."""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta, timezone
import sys
import os
import logging

# Add the project root to Python path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import (
    JWT_SECRET_KEY,
    JWT_REFRESH_SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS
)
from server.database.config import get_session_dependency
from server.models.user import User
from server.services.auth_service import AuthService
from server.services.token_service import TokenService
from server.services.api_key_service import ApiKeyService

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(data.get("sub", data.get("user_id", "unknown"))),  # Ensure subject is always present
        "type": "access"
    })
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(data.get("sub", data.get("user_id", "unknown"))),  # Ensure subject is always present
        "type": "refresh"
    })
    encoded_jwt = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str, secret_key: str = JWT_SECRET_KEY) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.PyJWTError:  # Fixed: changed from jwt.JWTError to jwt.PyJWTError
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}"
        )

def verify_refresh_token(token: str) -> Optional[dict]:
    """Verify a refresh token and return the payload."""
    try:
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:  # Fixed: changed from jwt.JWTError to jwt.PyJWTError
        return None

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_session_dependency)
) -> User:
    """Get the current authenticated user from either API key or JWT Bearer token."""
    
    # Try API key authentication first
    api_key = x_api_key or request.headers.get('X-API-Key') or request.headers.get('x-api-key')
    
    if api_key:
        user = ApiKeyService.validate_api_key(db, api_key)
        if user:
            return user
    
    # Fall back to JWT Bearer token authentication
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials. Please provide either a valid API key or JWT Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if it's a Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # Check if token is blacklisted (invalidated after logout)
    if TokenService.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = verify_token(token)
    except HTTPException:
        # Re-raise HTTP exceptions from verify_token
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_user_optional(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_session_dependency)
) -> Optional[User]:
    """Get the current authenticated user from either API key or JWT Bearer token, or return None if no valid credentials."""
    
    try:
        # Try API key authentication first
        if x_api_key:
            try:
                user = ApiKeyService.validate_api_key(db, x_api_key)
                if user:
                    return user
            except Exception:
                # If API key validation fails, continue to JWT or return None
                pass
        
        # Try JWT authentication if Authorization header is present
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]  # Remove "Bearer " prefix
            
            # Check if token is blacklisted (invalidated after logout)
            if TokenService.is_token_blacklisted(token):
                return None  # Return None instead of throwing error
            
            try:
                payload = verify_token(token)
            except Exception:
                # If token verification fails, return None instead of throwing error
                return None
            
            # Check token type
            if payload.get("type") != "access":
                return None
            
            user_id: int = payload.get("sub")
            if user_id is None:
                return None
            
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_active:
                    return user
            except Exception:
                # If database query fails, return None
                return None
        
        # If neither API key nor valid JWT token is provided, return None
        return None
        
    except Exception:
        # Catch any other unexpected errors and return None
        return None

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def require_same_user(user_id: int, current_user: User = Depends(get_current_user)) -> User:
    """Require that the current user is the same as the requested user_id."""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own data"
        )
    return current_user

def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Require that the current user has a verified email."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user
