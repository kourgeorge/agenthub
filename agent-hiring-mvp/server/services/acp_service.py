"""ACP (Agent Communication Protocol) service."""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ACPService:
    """Service for managing ACP protocol information."""
    
    def __init__(self, db=None):
        """Initialize ACP service. Database parameter kept for compatibility."""
        self.db = db
    
    def get_protocol_info(self) -> Dict[str, Any]:
        """Get ACP protocol information."""
        return {
            "protocol": "ACP",
            "version": "1.0.0",
            "name": "Agent Communication Protocol",
            "description": "Standard protocol for agent communication",
            "status": "active",
            "features": [
                "docker_deployment",
                "agent_proxy",
                "health_checks",
                "direct_messaging"
            ]
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get ACP protocol capabilities."""
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