"""Authentication Middleware Package."""

from .auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_refresh_token,
    get_current_user,
    get_current_user_optional,
    get_current_active_user,
    require_same_user,
    require_verified_user,
    get_current_user_required
)

from .permissions import (
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    require_admin,
    require_agent_creator,
    require_agent_owner,
    require_agent_permission,
    require_billing_permission,
    require_admin_permission,
    require_hiring_permission,
    require_deployment_permission,
    require_execution_permission,
    require_user_permission
)

__all__ = [
    # Auth middleware
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "verify_refresh_token",
    "get_current_user",
    "get_current_user_optional",
    "get_current_active_user",
    "require_same_user",
    "require_verified_user",
    "get_current_user_required",
    
    # Permission middleware
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
    "require_admin",
    "require_agent_creator",
    "require_agent_owner",
    "require_agent_permission",
    "require_billing_permission",
    "require_admin_permission",
    "require_hiring_permission",
    "require_deployment_permission",
    "require_execution_permission",
    "require_user_permission",
]
