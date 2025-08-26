"""Permission middleware for enforcing access control on API endpoints."""

import logging
from functools import wraps
from typing import Optional, List, Union
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import inspect

from ..database.config import get_session_dependency
from ..models.user import User
from ..middleware.auth import get_current_user
from ..services.permission_service import PermissionService

logger = logging.getLogger(__name__)


def require_permission(permission: str):
    """
    Decorator to require a specific permission.
    
    Args:
        permission: Permission string required (e.g., "agent:create")
        
    Usage:
        @router.post("/agents")
        @require_permission("agent:create")
        def create_agent(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # Debug logging
            logger.info(f"Permission decorator debug - Args: {args}, Kwargs: {kwargs}")
            logger.info(f"Permission decorator debug - Found current_user: {current_user}, db: {db}")
            logger.info(f"Permission decorator debug - Required permission: {permission}")
            
            # If not found in parameters, this is a critical error
            # The permission decorator should only be used with functions that have these dependencies
            if not current_user or not db:
                logger.error(f"Permission decorator failed to find current_user or db. Args: {args}, Kwargs: {kwargs}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters. Ensure dependencies are properly injected."
                )
            
            # Check if user has the required permission
            if not PermissionService.has_permission(db, current_user.id, permission):
                logger.error(f"Permission denied for user {current_user.id}: {permission} required")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
            
            logger.debug(f"Permission check passed for user {current_user.id}: {permission}")
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # Debug logging
            logger.info(f"Permission decorator debug - Args: {args}, Kwargs: {kwargs}")
            logger.info(f"Permission decorator debug - Found current_user: {current_user}, db: {db}")
            logger.info(f"Permission decorator debug - Required permission: {permission}")
            
            # If not found in parameters, this is a critical error
            # The permission decorator should only be used with functions that have these dependencies
            if not current_user or not db:
                logger.error(f"Permission decorator failed to find current_user or db. Args: {args}, Kwargs: {kwargs}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters. Ensure dependencies are properly injected."
                )
            
            # Check if user has the required permission
            if not PermissionService.has_permission(db, current_user.id, permission):
                logger.error(f"Permission denied for user {current_user.id}: {permission} required")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
            
            logger.debug(f"Permission check passed for user {current_user.id}: {permission}")
            return func(*args, **kwargs)
        
        # Return the appropriate wrapper based on whether the function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def require_any_permission(permissions: List[str]):
    """
    Decorator to require any of the specified permissions.
    
    Args:
        permissions: List of permission strings, user must have at least one
        
    Usage:
        @router.get("/agents")
        @require_any_permission(["agent:read", "agent:admin"])
        def list_agents(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # If not found in parameters, try to get from dependencies
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters"
                )
            
            # Check if user has any of the required permissions
            if not PermissionService.has_any_permission(db, current_user.id, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: At least one of {permissions} required"
                )
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # If not found in parameters, try to get from dependencies
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters"
                )
            
            # Check if user has any of the required permissions
            if not PermissionService.has_any_permission(db, current_user.id, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: At least one of {permissions} required"
                )
            
            return func(*args, **kwargs)
        
        # Return the appropriate wrapper based on whether the function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def require_all_permissions(permissions: List[str]):
    """
    Decorator to require all of the specified permissions.
    
    Args:
        permissions: List of permission strings, user must have all
        
    Usage:
        @router.delete("/agents/{agent_id}")
        @require_all_permissions(["agent:delete", "agent:admin"])
        def delete_agent(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # If not found in parameters, try to get from dependencies
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters"
                )
            
            # Check if user has all of the required permissions
            if not PermissionService.has_all_permissions(db, current_user.id, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: All of {permissions} required"
                )
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # If not found in parameters, try to get from dependencies
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters"
                )
            
            # Check if user has all of the required permissions
            if not PermissionService.has_all_permissions(db, current_user.id, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: All of {permissions} required"
                )
            
            return func(*args, **kwargs)
        
        # Return the appropriate wrapper based on whether the function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def require_role(role_name: str):
    """
    Decorator to require a specific role.
    
    Args:
        role_name: Name of the role required (e.g., "admin")
        
    Usage:
        @router.get("/admin/users")
        @require_role("admin")
        def list_users(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # If not found in parameters, try to get from dependencies
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters"
                )
            
            # Check if user has the required role
            if not PermissionService.has_role(db, current_user.id, role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role_name}"
                )
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get the current user from the function parameters
            current_user = None
            db = None
            
            # Find current_user and db in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
            
            # If not found in parameters, try to get from dependencies
            if not current_user or not db:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission decorator requires current_user and db parameters"
                )
            
            # Check if user has the required role
            if not PermissionService.has_role(db, current_user.id, role_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role_name}"
                )
            
            return func(*args, **kwargs)
        
        # Return the appropriate wrapper based on whether the function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def require_admin():
    """
    Decorator to require admin role.
    
    Usage:
        @router.get("/admin/system")
        @require_admin()
        def get_system_info(...):
            ...
    """
    return require_role("admin")


def require_agent_creator():
    """
    Decorator to require agent_creator role.
    
    Usage:
        @router.post("/agents")
        @require_agent_creator()
        def create_agent(...):
            ...
    """
    return require_role("agent_creator")


def require_agent_owner():
    """
    Decorator to require that the user owns the agent being accessed.
    This is a special case that checks agent ownership rather than permissions.
    
    Usage:
        @router.put("/agents/{agent_id}")
        @require_agent_owner()
        def update_agent(agent_id: str, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get the current user and agent_id from the function parameters
            current_user = None
            db = None
            agent_id = None
            
            # Find current_user, db, and agent_id in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
                elif isinstance(arg, str):
                    agent_id = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
                elif key == "agent_id" and isinstance(value, str):
                    agent_id = value
            
            # If not found in parameters, this is a critical error
            if not current_user or not db or not agent_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Agent owner decorator requires current_user, db, and agent_id parameters"
                )
            
            # Check if user owns the agent
            from ..models.agent import Agent
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            if agent.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only modify agents you own"
                )
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Get the current user and agent_id from the function parameters
            current_user = None
            db = None
            agent_id = None
            
            # Find current_user, db, and agent_id in function parameters
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Session):
                    db = arg
                elif isinstance(arg, str):
                    agent_id = arg
            
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif isinstance(value, Session):
                    db = value
                elif key == "agent_id" and isinstance(value, str):
                    agent_id = value
            
            # If not found in parameters, this is a critical error
            if not current_user or not db or not agent_id:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Agent owner decorator requires current_user, db, and agent_id parameters"
                )
            
            # Check if user owns the agent
            from ..models.agent import Agent
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found"
                )
            
            if agent.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only modify agents you own"
                )
            
            return func(*args, **kwargs)
        
        # Return the appropriate wrapper based on whether the function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


# Convenience decorators for common permission patterns
def require_agent_permission(action: str):
    """
    Convenience decorator for agent-related permissions.
    
    Args:
        action: Action required (e.g., "create", "read", "update", "delete")
        
    Usage:
        @router.post("/agents")
        @require_agent_permission("create")
        def create_agent(...):
            ...
    """
    return require_permission(f"agent:{action}")


def require_billing_permission(action: str):
    """
    Convenience decorator for billing-related permissions.
    
    Args:
        action: Action required (e.g., "view", "manage")
        
    Usage:
        @router.get("/billing")
        @require_billing_permission("view")
        def get_billing(...):
            ...
    """
    return require_permission(f"billing:{action}")


def require_admin_permission(action: str):
    """
    Convenience decorator for admin-related permissions.
    
    Args:
        action: Action required (e.g., "view", "manage", "system")
        
    Usage:
        @router.get("/admin/users")
        @require_admin_permission("view")
        def list_users(...):
            ...
    """
    return require_permission(f"admin:{action}")


def require_hiring_permission(action: str):
    """
    Convenience decorator for hiring-related permissions.
    
    Args:
        action: Action required (e.g., "create", "view", "manage", "cancel")
        
    Usage:
        @router.post("/hiring")
        @require_hiring_permission("create")
        def create_hiring(...):
            ...
    """
    return require_permission(f"hiring:{action}")


def require_deployment_permission(action: str):
    """
    Convenience decorator for deployment-related permissions.
    
    Args:
        action: Action required (e.g., "create", "start", "stop", "suspend", "delete", "monitor")
        
    Usage:
        @router.post("/deployments")
        @require_deployment_permission("create")
        def create_deployment(...):
            ...
    """
    return require_permission(f"deployment:{action}")


def require_execution_permission(action: str):
    """
    Convenience decorator for execution-related permissions.
    
    Args:
        action: Action required (e.g., "create", "view", "cancel", "logs")
        
    Usage:
        @router.post("/executions")
        @require_execution_permission("create")
        def create_execution(...):
            ...
    """
    return require_permission(f"execution:{action}")


def require_user_permission(action: str):
    """
    Convenience decorator for user-related permissions.
    
    Args:
        action: Action required (e.g., "profile", "settings", "api_keys")
        
    Usage:
        @router.get("/profile")
        @require_user_permission("profile")
        def get_profile(...):
            ...
    """
    return require_permission(f"user:{action}")
