"""ACP (Agent Communication Protocol) API endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/acp", tags=["acp"])


@router.get("/discovery")
def acp_discovery():
    """ACP protocol discovery endpoint."""
    return {
        "protocol": "ACP",
        "version": "1.0.0",
        "name": "Agent Communication Protocol",
        "description": "Standard protocol for agent communication",
        "documentation": "https://docs.agenthub.dev/acp",
        "endpoints": {
            "discovery": "/api/v1/acp/discovery",
            "capabilities": "/api/v1/acp/capabilities"
        }
    }


@router.get("/capabilities")
def acp_capabilities():
    """ACP protocol capabilities endpoint."""
    return {
        "capabilities": [
            "agent_deployment",
            "direct_communication",
            "health_monitoring",
            "proxy_routing"
        ],
        "supported_versions": ["1.0.0"],
        "features": {
            "docker_deployment": True,
            "agent_proxy": True,
            "health_checks": True,
            "direct_messaging": True
        },
        "communication_methods": {
            "agent_proxy": "/api/v1/agent-proxy/{hiring_id}",
            "deployment": "/api/v1/deployment"
        }
    } 