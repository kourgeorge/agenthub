"""API package for the Agent Hiring System."""

from .agents import router as agents_router
from .hiring import router as hiring_router
from .execution import router as execution_router
from .acp import router as acp_router
from .users import router as users_router
from .billing import router as billing_router
from .deployment import router as deployment_router
from .agent_proxy import router as agent_proxy_router
from .resources import router as resources_router
from .auth import router as auth_router
from .api_keys import router as api_keys_router
from .stats import router as stats_router
from .earnings import router as earnings_router
from .contact import router as contact_router

__all__ = [
    "agents_router",
    "hiring_router",
    "execution_router", 
    "acp_router",
    "users_router",
    "billing_router",
    "deployment_router",
    "agent_proxy_router",
    "resources_router",
    "auth_router",
    "api_keys_router",
    "stats_router",
    "earnings_router",
    "contact_router",
] 