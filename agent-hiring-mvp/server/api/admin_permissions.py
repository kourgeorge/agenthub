"""Admin permissions API endpoints for managing system permissions and roles."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database import get_db
from ..models.user import User
from ..models.role import Role
from ..models.permission import Permission
from ..models.user_role import UserRole
from ..middleware.auth import get_current_user
from ..middleware.permissions import require_admin_permission
from ..services.permission_service import PermissionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for request validation
class PermissionCreateRequest(BaseModel):
    resource: str = Field(..., description="Resource name (e.g., 'agent', 'billing')")
    action: str = Field(..., description="Action name (e.g., 'create', 'read')")
    description: str = Field(..., description="Description of the permission")

class PermissionUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, description="Description of the permission")
    is_active: Optional[bool] = Field(None, description="Whether the permission is active")

class RoleCreateRequest(BaseModel):
    name: str = Field(..., description="Name of the role")
    description: str = Field(..., description="Description of the role")
    permissions: List[str] = Field(default=[], description="List of permission names")

class RoleUpdateRequest(BaseModel):
    description: Optional[str] = Field(None, description="Description of the role")
    permissions: Optional[List[str]] = Field(None, description="List of permission names")
    is_active: Optional[bool] = Field(None, description="Whether the role is active")

class RoleAssignmentRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user to assign the role to")
    role_name: str = Field(..., description="Name of the role to assign")


@router.get("/permissions")
@require_admin_permission("view")
async def get_all_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all system permissions (admin only)."""
    try:
        permissions = db.query(Permission).order_by(Permission.resource, Permission.action).all()
        
        return {
            "success": True,
            "permissions": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "resource": p.resource,
                    "action": p.action,
                    "is_active": p.is_active,
                    "is_system_permission": p.is_system_permission,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in permissions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch permissions: {str(e)}"
        )


@router.post("/permissions")
@require_admin_permission("manage")
async def create_permission(
    permission_data: PermissionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new permission (admin only)."""
    try:
        # Check if permission already exists
        existing = db.query(Permission).filter(
            and_(
                Permission.resource == permission_data.resource,
                Permission.action == permission_data.action
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Permission already exists"
            )
        
        # Validate resource and action format
        resource = permission_data.resource.strip().lower()
        action = permission_data.action.strip().lower()
        
        # Check for invalid characters
        if not resource.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource name can only contain letters, numbers, underscores, and hyphens"
            )
        
        if not action.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action name can only contain letters, numbers, underscores, and hyphens"
            )
        
        # Create permission name
        permission_name = f"{resource}:{action}"
        
        # Create new permission
        new_permission = Permission(
            name=permission_name,
            description=permission_data.description.strip(),
            resource=resource,
            action=action,
            is_active=True,
            is_system_permission=False
        )
        
        db.add(new_permission)
        db.commit()
        db.refresh(new_permission)
        
        return {
            "success": True,
            "permission": {
                "id": new_permission.id,
                "name": new_permission.name,
                "description": new_permission.description,
                "resource": new_permission.resource,
                "action": new_permission.action,
                "is_active": new_permission.is_active,
                "is_system_permission": new_permission.is_system_permission,
                "created_at": new_permission.created_at.isoformat(),
                "updated_at": new_permission.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating permission: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create permission: {str(e)}"
        )


@router.put("/permissions/{permission_id}")
@require_admin_permission("manage")
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing permission (admin only)."""
    try:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Prevent modification of system permissions
        if permission.is_system_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system permissions"
            )
        
        # Update fields
        if permission_data.description is not None:
            permission.description = permission_data.description
        if permission_data.is_active is not None:
            permission.is_active = permission_data.is_active
        
        permission.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(permission)
        
        return {
            "success": True,
            "permission": {
                "id": permission.id,
                "name": permission.name,
                "description": permission.description,
                "resource": permission.resource,
                "action": permission.action,
                "is_active": permission.is_active,
                "is_system_permission": permission.is_system_permission,
                "created_at": permission.created_at.isoformat(),
                "updated_at": permission.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating permission: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update permission: {str(e)}"
        )


@router.delete("/permissions/{permission_id}")
@require_admin_permission("manage")
async def delete_permission(
    permission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a permission (admin only)."""
    try:
        permission = db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found"
            )
        
        # Prevent deletion of system permissions
        if permission.is_system_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system permissions"
            )
        
        # Check if permission is used by any roles
        roles_using_permission = db.query(Role).filter(
            Role.permissions.contains([permission.name])
        ).all()
        
        if roles_using_permission:
            role_names = [role.name for role in roles_using_permission]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete permission used by roles: {', '.join(role_names)}"
            )
        
        db.delete(permission)
        db.commit()
        
        return {"success": True, "message": "Permission deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting permission: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete permission: {str(e)}"
        )


@router.get("/roles")
@require_admin_permission("view")
async def get_all_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all system roles (admin only)."""
    try:
        roles = db.query(Role).order_by(Role.name).all()
        
        return {
            "success": True,
            "roles": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "permissions": r.permissions or [],
                    "is_active": r.is_active,
                    "is_system_role": r.is_system_role,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat()
                }
                for r in roles
            ]
        }
        
    except Exception as e:
        logger.error(f"Error fetching roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch roles: {str(e)}"
        )


@router.post("/roles")
@require_admin_permission("manage")
async def create_role(
    role_data: RoleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new role (admin only)."""
    try:
        logger.info(f"Creating new role: name='{role_data.name}', description='{role_data.description}', permissions={role_data.permissions}")
        logger.debug(f"Full role data: {role_data}")
        # Validate role name format
        role_name = role_data.name.strip().lower()
        
        # Check for invalid characters
        if not role_name.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name can only contain letters, numbers, underscores, and hyphens"
            )
        
        # Check if role already exists
        existing = db.query(Role).filter(Role.name == role_name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role already exists"
            )
        
        # Validate permissions exist
        permissions = role_data.permissions
        if permissions:
            existing_permissions = db.query(Permission).filter(
                Permission.name.in_(permissions)
            ).all()
            if len(existing_permissions) != len(permissions):
                existing_names = [p.name for p in existing_permissions]
                missing = [p for p in permissions if p not in existing_names]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid permissions: {missing}"
                )
        
        # Create new role
        new_role = Role(
            name=role_data.name,
            description=role_data.description.strip(),
            permissions=permissions,
            is_active=True,
            is_system_role=False
        )
        
        db.add(new_role)
        db.commit()
        db.refresh(new_role)
        
        return {
            "success": True,
            "role": {
                "id": new_role.id,
                "name": new_role.name,
                "description": new_role.description,
                "permissions": new_role.permissions or [],
                "is_active": new_role.is_active,
                "is_system_role": new_role.is_system_role,
                "created_at": new_role.created_at.isoformat(),
                "updated_at": new_role.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}"
        )


@router.put("/roles/{role_id}")
@require_admin_permission("manage")
async def update_role(
    role_id: int,
    role_data: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing role (admin only)."""
    try:
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Prevent modification of system roles
        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify system roles"
            )
        
        # Update fields
        if role_data.description is not None:
            role.description = role_data.description
        if role_data.permissions is not None:
            # Validate permissions exist
            permissions = role_data.permissions
            if permissions:
                existing_permissions = db.query(Permission).filter(
                    Permission.name.in_(permissions)
                ).all()
                if len(existing_permissions) != len(permissions):
                    existing_names = [p.name for p in existing_permissions]
                    missing = [p for p in permissions if p not in existing_names]
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid permissions: {missing}"
                    )
            role.permissions = permissions
        if role_data.is_active is not None:
            role.is_active = role_data.is_active
        
        role.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(role)
        
        return {
            "success": True,
            "role": {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions or [],
                "is_active": role.is_active,
                "is_system_role": role.is_system_role,
                "created_at": role.created_at.isoformat(),
                "updated_at": role.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}"
        )


@router.delete("/roles/{role_id}")
@require_admin_permission("manage")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a role (admin only)."""
    try:
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Prevent deletion of system roles
        if role.is_system_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete system roles"
            )
        
        # Check if role is assigned to any users
        users_with_role = db.query(UserRole).filter(
            and_(
                UserRole.role_id == role_id,
                UserRole.is_active == True
            )
        ).all()
        
        if users_with_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete role that is assigned to users"
            )
        
        db.delete(role)
        db.commit()
        
        return {"success": True, "message": "Role deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting role: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role: {str(e)}"
        )


@router.get("/users")
@require_admin_permission("view")
async def get_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all system users with their roles and permissions (admin only)."""
    try:
        users = db.query(User).filter(User.is_active == True).all()
        
        user_data = []
        for user in users:
            # Get user roles and permissions
            roles = PermissionService.get_user_roles(db, user.id)
            permissions = PermissionService.get_user_permissions(db, user.id)
            
            user_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "roles": roles,
                "permissions": list(permissions)
            })
        
        return {
            "success": True,
            "users": user_data
        }
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.get("/user-roles")
@require_admin_permission("view")
async def get_all_user_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all user role assignments (admin only)."""
    try:
        logger.debug("Fetching all user role assignments...")
        
        # Use explicit join conditions to avoid ambiguity
        user_roles = db.query(UserRole).join(
            Role, UserRole.role_id == Role.id
        ).join(
            User, UserRole.user_id == User.id
        ).filter(
            UserRole.is_active == True
        ).all()
        
        logger.debug(f"Found {len(user_roles)} active user role assignments")
        
        result = {
            "success": True,
            "user_roles": [
                {
                    "user_id": ur.user_id,
                    "username": ur.user.username,
                    "email": ur.user.email,
                    "role_name": ur.role.name,
                    "assigned_at": ur.assigned_at.isoformat() if ur.assigned_at else None,
                    "expires_at": ur.expires_at.isoformat() if ur.expires_at else None,
                    "is_active": ur.is_active
                }
                for ur in user_roles
            ]
        }
        
        logger.debug("Successfully fetched user role assignments")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching user roles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user roles: {str(e)}"
        )


@router.post("/user-roles")
@require_admin_permission("manage")
async def assign_role_to_user(
    assignment_data: RoleAssignmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Assign a role to a user (admin only)."""
    try:
        logger.info(f"Received role assignment request: user_id={assignment_data.user_id}, role_name={assignment_data.role_name}")
        logger.debug(f"Full assignment data: {assignment_data}")
        
        user_id = assignment_data.user_id
        role_name = assignment_data.role_name
        
        logger.debug(f"Extracted user_id: {user_id} (type: {type(user_id)}), role_name: {role_name} (type: {type(role_name)})")
        
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        logger.debug(f"Found user: {user.username} (ID: {user.id})")
        
        # Check if role exists
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{role_name}' not found"
            )
        
        logger.debug(f"Found role: {role.name} (ID: {role.id})")
        
        # Check if user already has this role
        existing_assignment = db.query(UserRole).join(Role).filter(
            and_(
                UserRole.user_id == user_id,
                Role.name == role_name,
                UserRole.is_active == True
            )
        ).first()
        
        if existing_assignment:
            logger.debug(f"User {user.username} already has role {role_name}")
            return {"success": True, "message": "User already has this role"}
        
        # Assign role using PermissionService
        success = PermissionService.assign_role_to_user(
            db, user_id, role_name, current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to assign role"
            )
        
        logger.debug(f"Successfully assigned role {role_name} to user {user.username}")
        return {"success": True, "message": "Role assigned successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning role: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}"
        )


@router.delete("/user-roles/{user_id}/{role_name}")
@require_admin_permission("manage")
async def remove_role_from_user(
    user_id: int,
    role_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a role from a user (admin only)."""
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove role using PermissionService
        success = PermissionService.remove_role_from_user(db, user_id, role_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove role"
            )
        
        return {"success": True, "message": "Role removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}"
        )
