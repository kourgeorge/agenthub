"""Permission service for managing user permissions and roles."""

from typing import List, Optional, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.user import User
from ..models.role import Role
from ..models.user_role import UserRole
from ..models.permission import Permission


class PermissionService:
    """Service for managing user permissions and roles."""
    
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> Set[str]:
        """
        Get all permissions for a user based on their active roles.
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            Set of permission strings (e.g., {"agent:create", "billing:view"})
        """
        try:
            # Get all active user roles
            user_roles = db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True
                )
            ).all()
            
            permissions = set()
            
            for user_role in user_roles:
                # Check if role is expired
                if user_role.is_expired():
                    continue
                
                # Get the role and its permissions
                role = db.query(Role).filter(
                    and_(
                        Role.id == user_role.role_id,
                        Role.is_active == True
                    )
                ).first()
                
                if role and role.permissions:
                    permissions.update(role.permissions)
            
            return permissions
            
        except Exception as e:
            # Log error and return empty set
            print(f"Error getting user permissions: {e}")
            return set()
    
    @staticmethod
    def has_permission(db: Session, user_id: int, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            db: Database session
            user_id: ID of the user
            permission: Permission string to check (e.g., "agent:create")
            
        Returns:
            True if user has the permission, False otherwise
        """
        try:
            user_permissions = PermissionService.get_user_permissions(db, user_id)
            
            # Check for wildcard permission (*:*)
            if "*:*" in user_permissions:
                print(f"DEBUG: User {user_id} has wildcard permission *:*")
                return True
            
            # Check for specific permission
            has_perm = permission in user_permissions
            print(f"DEBUG: User {user_id} permission check for '{permission}': {has_perm}")
            print(f"DEBUG: User {user_id} has permissions: {user_permissions}")
            
            return has_perm
            
        except Exception as e:
            print(f"Error checking permission: {e}")
            return False
    
    @staticmethod
    def has_any_permission(db: Session, user_id: int, permissions: List[str]) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            db: Database session
            user_id: ID of the user
            permissions: List of permission strings to check
            
        Returns:
            True if user has at least one of the permissions, False otherwise
        """
        try:
            user_permissions = PermissionService.get_user_permissions(db, user_id)
            return any(permission in user_permissions for permission in permissions)
            
        except Exception as e:
            print(f"Error checking permissions: {e}")
            return False
    
    @staticmethod
    def has_all_permissions(db: Session, user_id: int, permissions: List[str]) -> bool:
        """
        Check if user has all of the specified permissions.
        
        Args:
            db: Database session
            user_id: ID of the user
            permissions: List of permission strings to check
            
        Returns:
            True if user has all permissions, False otherwise
        """
        try:
            user_permissions = PermissionService.get_user_permissions(db, user_id)
            return all(permission in user_permissions for permission in permissions)
            
        except Exception as e:
            print(f"Error checking permissions: {e}")
            return False
    
    @staticmethod
    def has_role(db: Session, user_id: int, role_name: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            db: Database session
            user_id: ID of the user
            role_name: Name of the role to check
            
        Returns:
            True if user has the role, False otherwise
        """
        try:
            # Get user's active roles with explicit join
            user_roles = db.query(UserRole).join(
                Role, UserRole.role_id == Role.id
            ).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True,
                    Role.name == role_name,
                    Role.is_active == True
                )
            ).all()
            
            # Check if any valid roles exist
            for user_role in user_roles:
                if user_role.is_valid():
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error checking role: {e}")
            return False
    
    @staticmethod
    def get_user_roles(db: Session, user_id: int) -> List[str]:
        """
        Get all role names for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            List of role names
        """
        try:
            # Get user's active roles with explicit join
            user_roles = db.query(UserRole).join(
                Role, UserRole.role_id == Role.id
            ).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True,
                    Role.is_active == True
                )
            ).all()
            
            role_names = []
            for user_role in user_roles:
                if user_role.is_valid():
                    role_names.append(user_role.role.name)
            
            return role_names
            
        except Exception as e:
            print(f"Error getting user roles: {e}")
            return []
    
    @staticmethod
    def get_user_role_details(db: Session, user_id: int) -> List[dict]:
        """
        Get detailed role information for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            List of role details including name, description, assigned date, etc.
        """
        try:
            # Get user's active roles with details and explicit join
            user_roles = db.query(UserRole).join(
                Role, UserRole.role_id == Role.id
            ).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True,
                    Role.is_active == True
                )
            ).all()
            
            role_details = []
            for user_role in user_roles:
                if user_role.is_valid():
                    role_details.append({
                        "role_name": user_role.role.name,
                        "role_description": user_role.role.description,
                        "assigned_at": user_role.assigned_at.isoformat() if user_role.assigned_at else None,
                        "assigned_by": user_role.assigned_by,
                        "expires_at": user_role.expires_at.isoformat() if user_role.expires_at else None,
                        "permissions": user_role.role.permissions or []
                    })
            
            return role_details
            
        except Exception as e:
            print(f"Error getting user role details: {e}")
            return []
    
    @staticmethod
    def assign_role_to_user(
        db: Session, 
        user_id: int, 
        role_name: str, 
        assigned_by: Optional[int] = None,
        expires_at: Optional[str] = None
    ) -> bool:
        """
        Assign a role to a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            role_name: Name of the role to assign
            assigned_by: ID of the user assigning the role (optional)
            expires_at: ISO string for role expiration (optional)
            
        Returns:
            True if role was assigned successfully, False otherwise
        """
        try:
            # Check if role exists
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                print(f"Role '{role_name}' not found")
                return False
            
            # Check if user already has this role
            existing_user_role = db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.id
                )
            ).first()
            
            if existing_user_role:
                # Update existing role assignment
                existing_user_role.is_active = True
                existing_user_role.assigned_by = assigned_by
                if expires_at:
                    from datetime import datetime
                    try:
                        existing_user_role.expires_at = datetime.fromisoformat(expires_at)
                    except ValueError as e:
                        print(f"Invalid expires_at format: {expires_at}, error: {e}")
                        return False
            else:
                # Create new role assignment
                from datetime import datetime
                expires_datetime = None
                if expires_at:
                    try:
                        expires_datetime = datetime.fromisoformat(expires_at)
                    except ValueError as e:
                        print(f"Invalid expires_at format: {expires_at}, error: {e}")
                        return False
                
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role.id,
                    assigned_by=assigned_by,
                    expires_at=expires_datetime
                )
                db.add(user_role)
            
            db.commit()
            return True
            
        except Exception as e:
            print(f"Error assigning role: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def remove_role_from_user(db: Session, user_id: int, role_name: str) -> bool:
        """
        Remove a role from a user (deactivate the role assignment).
        
        Args:
            db: Database session
            user_id: ID of the user
            role_name: Name of the role to remove
            
        Returns:
            True if role was removed successfully, False otherwise
        """
        try:
            # Find the role
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                print(f"Role '{role_name}' not found")
                return False
            
            # Find and deactivate the user role assignment
            user_role = db.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.id
                )
            ).first()
            
            if user_role:
                user_role.is_active = False
                db.commit()
                return True
            else:
                print(f"User {user_id} does not have role '{role_name}'")
                return False
                
        except Exception as e:
            print(f"Error removing role: {e}")
            db.rollback()
            return False
