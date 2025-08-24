"""Permission seeding for the Agent Hiring System."""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.user import User
from ..models.role import Role
from ..models.permission import Permission
from ..models.user_role import UserRole

logger = logging.getLogger(__name__)


class AdminSettings:
    """Admin user configuration from environment variables."""
    
    def __init__(self):
        import os
        self.email = os.getenv("ADMIN_EMAIL", "admin@agenthub.net")
        self.username = os.getenv("ADMIN_USERNAME", "admin")
        self.password = os.getenv("ADMIN_PASSWORD", "q1q1q1")
        self.full_name = os.getenv("ADMIN_FULL_NAME", "System Administrator")


class PermissionSeeder:
    """Seeder class for populating default roles and permissions."""
    
    # Default permissions organized by resource
    DEFAULT_PERMISSIONS = {
        "agent": [
            "create", "read", "update", "delete", "approve", "reject"
        ],
        "billing": [
            "view", "manage", "invoices", "payments"
        ],
        "admin": [
            "view", "manage", "users", "system", "analytics"
        ],
        "deployment": [
            "create", "start", "stop", "suspend", "delete", "monitor"
        ],
        "execution": [
            "create", "view", "cancel", "logs"
        ],
        "hiring": [
            "create", "view", "manage", "cancel"
        ],
        "user": [
            "profile", "settings", "api_keys"
        ]
    }
    
    # Default roles with their permissions
    DEFAULT_ROLES = {
        "admin": {
            "description": "Full system administrator with all permissions",
            "permissions": ["*:*"],  # Wildcard for all permissions
            "is_system_role": True
        },
        "user": {
            "description": "Basic user with standard permissions",
            "permissions": [
                "agent:read", "agent:create", "agent:update", "agent:delete", "agent:publish",
                "deployment:create", "deployment:start", "deployment:stop", 
                "deployment:suspend", "deployment:delete", "deployment:monitor",
                "execution:create", "execution:view", "execution:cancel", "execution:logs",
                "hiring:create", "hiring:view", "hiring:manage", "hiring:cancel",
                "billing:view", "billing:manage", "billing:invoices", "billing:payments",
                "user:profile", "user:settings", "user:api_keys"
            ],
            "is_system_role": True
        }
    }
    
    @classmethod
    def seed_permissions(cls, db: Session) -> bool:
        """
        Seed the database with default permissions.
        
        Args:
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting permission seeding...")
            
            # Create permissions for each resource
            for resource, actions in cls.DEFAULT_PERMISSIONS.items():
                for action in actions:
                    permission_name = f"{resource}:{action}"
                    
                    # Check if permission already exists
                    existing = db.query(Permission).filter(
                        Permission.name == permission_name
                    ).first()
                    
                    if not existing:
                        permission = Permission(
                            name=permission_name,
                            description=f"Permission to {action} {resource}",
                            resource=resource,
                            action=action,
                            is_system_permission=True
                        )
                        db.add(permission)
                        logger.info(f"Created permission: {permission_name}")
                    else:
                        logger.info(f"Permission already exists: {permission_name}")
            
            # Create wildcard permission for admin
            wildcard_permission = db.query(Permission).filter(
                Permission.name == "*:*"
            ).first()
            
            if not wildcard_permission:
                wildcard_permission = Permission(
                    name="*:*",
                    description="Wildcard permission for all actions",
                    resource="*",
                    action="*",
                    is_system_permission=True
                )
                db.add(wildcard_permission)
                logger.info("Created wildcard permission: *:*")
            
            # Use merge instead of commit to handle concurrent access gracefully
            try:
                db.commit()
                logger.info("Permission seeding completed successfully")
                return True
            except Exception as commit_error:
                # If commit fails due to concurrent access, rollback and try to continue
                logger.warning(f"Commit failed during permission seeding (likely concurrent access): {commit_error}")
                db.rollback()
                
                # Check if permissions were actually created by another process
                if cls._check_permissions_exist(db):
                    logger.info("Permissions already exist from another process, continuing...")
                    return True
                else:
                    logger.error("Failed to create permissions and they don't exist")
                    return False
            
        except Exception as e:
            logger.error(f"Error seeding permissions: {e}")
            try:
                db.rollback()
            except:
                pass
            return False
    
    @classmethod
    def _check_permissions_exist(cls, db: Session) -> bool:
        """Check if basic permissions exist in the database."""
        try:
            # Check if we have at least some basic permissions
            basic_permissions = ["agent:read", "agent:create", "admin:view"]
            existing_count = db.query(Permission).filter(
                Permission.name.in_(basic_permissions)
            ).count()
            return existing_count > 0
        except Exception as e:
            logger.error(f"Error checking if permissions exist: {e}")
            return False
    
    @classmethod
    def seed_roles(cls, db: Session) -> bool:
        """
        Seed the database with default roles.
        
        Args:
            db: Database session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting role seeding...")
            
            # Create roles with their permissions
            for role_name, role_data in cls.DEFAULT_ROLES.items():
                # Check if role already exists
                existing_role = db.query(Role).filter(Role.name == role_name).first()
                
                if not existing_role:
                    role = Role(
                        name=role_name,
                        description=role_data["description"],
                        permissions=role_data["permissions"],
                        is_system_role=role_data["is_system_role"]
                    )
                    db.add(role)
                    logger.info(f"Created role: {role_name}")
                else:
                    # Update existing role permissions if needed
                    existing_role.permissions = role_data["permissions"]
                    existing_role.description = role_data["description"]
                    logger.info(f"Updated role: {role_name}")
            
            # Use merge instead of commit to handle concurrent access gracefully
            try:
                db.commit()
                logger.info("Role seeding completed successfully")
                return True
            except Exception as commit_error:
                # If commit fails due to concurrent access, rollback and try to continue
                logger.warning(f"Commit failed during role seeding (likely concurrent access): {commit_error}")
                db.rollback()
                
                # Check if roles were actually created by another process
                if cls._check_roles_exist(db):
                    logger.info("Roles already exist from another process, continuing...")
                    return True
                else:
                    logger.error("Failed to create roles and they don't exist")
                    return False
            
        except Exception as e:
            logger.error(f"Error seeding roles: {e}")
            try:
                db.rollback()
            except:
                pass
            return False
    
    @classmethod
    def _check_roles_exist(cls, db: Session) -> bool:
        """Check if basic roles exist in the database."""
        try:
            # Check if we have at least some basic roles
            basic_roles = ["admin", "user"]
            existing_count = db.query(Role).filter(
                Role.name.in_(basic_roles)
            ).count()
            return existing_count > 0
        except Exception as e:
            logger.error(f"Error checking if roles exist: {e}")
            return False
    
    @classmethod
    def assign_default_role_to_user(cls, db: Session, user_id: int, role_name: str = "user") -> bool:
        """
        Assign a default role to a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            role_name: Name of the role to assign (defaults to "user")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if role exists
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                logger.error(f"Role '{role_name}' not found")
                return False
            
            # Check if user already has this role
            existing_user_role = db.query(UserRole).filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role.id
            ).first()
            
            if not existing_user_role:
                user_role = UserRole(
                    user_id=user_id,
                    role_id=role.id,
                    assigned_at=datetime.now(timezone.utc)
                )
                db.add(user_role)
                logger.info(f"Assigned role '{role_name}' to user {user_id}")
            else:
                logger.info(f"User {user_id} already has role '{role_name}'")
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error assigning role to user: {e}")
            db.rollback()
            return False
    
    @classmethod
    def create_admin_user(cls, db: Session, email: str = None, password: str = None, username: str = None, full_name: str = None) -> User:
        """
        Create an admin user with full permissions.
        
        Args:
            db: Database session
            email: Admin user email (defaults to ADMIN_EMAIL env var)
            password: Admin user password (defaults to ADMIN_PASSWORD env var)
            username: Admin username (defaults to ADMIN_USERNAME env var)
            full_name: Admin full name (defaults to ADMIN_FULL_NAME env var)
            
        Returns:
            Created User object or None if failed
        """
        try:
            from ..services.auth_service import AuthService
            
            # Use environment variables if not provided
            admin_settings = AdminSettings()
            email = email or admin_settings.email
            password = password or admin_settings.password
            username = username or admin_settings.username
            full_name = full_name or admin_settings.full_name
            
            # Create the user
            user = AuthService.create_user(
                db=db,
                email=email,
                password=password,
                username=username,
                full_name=full_name
            )
            
            # Assign admin role
            cls.assign_default_role_to_user(db, user.id, "admin")
            
            logger.info(f"Created admin user: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            return None
    
    @classmethod
    def seed_all(cls, db: Session) -> bool:
        """
        Run all seeding operations.
        
        Args:
            db: Database session
            
        Returns:
            True if all operations successful, False otherwise
        """
        try:
            logger.info("Starting complete permission system seeding...")
            
            # Seed permissions first
            if not cls.seed_permissions(db):
                logger.error("Failed to seed permissions")
                return False
            
            # Seed roles
            if not cls.seed_roles(db):
                logger.error("Failed to seed roles")
                return False
            
            # Check for admin users and ensure they have admin role
            try:
                # Always ensure admin user has admin role
                logger.info("Ensuring admin user has admin role...")
                
                # Get admin settings from environment
                admin_settings = AdminSettings()
                
                # Find or create admin user
                admin_user = db.query(User).filter(
                    User.email == admin_settings.email
                ).first()
                
                if not admin_user:
                    logger.info("Creating new admin user...")
                    admin_user = cls.create_admin_user(db)
                    if admin_user:
                        logger.info("Admin user created successfully")
                    else:
                        logger.warning("Failed to create admin user")
                        return False  # Fail if we can't create admin user
                else:
                    logger.info(f"Found existing admin user: {admin_user.email}")
                
                # ALWAYS ensure admin role is assigned (this is the key fix!)
                logger.info("Ensuring admin role assignment...")
                if cls.assign_default_role_to_user(db, admin_user.id, "admin"):
                    logger.info("Admin role assigned successfully")
                else:
                    logger.warning("Failed to assign admin role")
                    return False  # Fail if we can't assign admin role
                    
            except Exception as admin_error:
                logger.error(f"Admin user creation/role assignment failed: {admin_error}")
                return False  # Fail the entire seeding if admin setup fails
            
            logger.info("Complete permission system seeding successful")
            return True
            
        except Exception as e:
            logger.error(f"Error in complete seeding: {e}")
            return False

    @classmethod
    def is_system_initialized(cls, db: Session) -> bool:
        """
        Check if the permission system is fully initialized.
        
        Args:
            db: Database session
            
        Returns:
            True if system is initialized, False otherwise
        """
        try:
            # Check if admin role exists
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if not admin_role:
                return False
            
            # Check if wildcard permission exists
            wildcard_permission = db.query(Permission).filter(Permission.name == "*:*").first()
            if not wildcard_permission:
                return False
            
            # Check if there's at least one admin user
            admin_settings = AdminSettings()
            admin_user = db.query(User).filter(User.email == admin_settings.email).first()
            if not admin_user:
                return False
            
            # Check if admin user has admin role
            admin_user_role = db.query(UserRole).filter(
                UserRole.user_id == admin_user.id,
                UserRole.role_id == admin_role.id
            ).first()
            
            if not admin_user_role:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking system initialization: {e}")
            return False


def seed_permissions_cli():
    """CLI function for seeding permissions from command line."""
    import sys
    import os
    
    # Add project root to path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from server.database.config import get_session_dependency
    
    try:
        db = next(get_session_dependency())
        success = PermissionSeeder.seed_all(db)
        
        if success:
            print("✅ Permission system seeding completed successfully!")
        else:
            print("❌ Permission system seeding failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_permissions_cli()
