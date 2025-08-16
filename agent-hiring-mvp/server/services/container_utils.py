"""Container naming utilities for deployment services."""

import hashlib
from typing import Optional
from ..models.deployment import AgentDeployment


def generate_container_name(deployment: AgentDeployment, agent_type: Optional[str] = None) -> str:
    """
    Generate consistent container name for a deployment.
    
    Args:
        deployment: The deployment object
        agent_type: Optional override for agent type (if None, uses deployment.deployment_type)
    
    Returns:
        Container name in format: aghub-{agent_type_abbr}-user_{user_id}-id_{agent_id}-hire_{hiring_id}-{deployment_uuid[:8]}
        If too long, uses: aghub-{agent_type_abbr}-user_{user_id}-id_{agent_id}-{deployment_uuid_hash[:12]}
    """
    if agent_type is None:
        agent_type = deployment.deployment_type or "function"
    
    # Get user_id from the hiring relationship
    user_id = deployment.hiring.user_id if deployment.hiring else "anon"
    
    # Use abbreviated agent types for shorter names
    agent_type_abbr = {
        "persistent": "persis",
        "function": "func", 
        "acp": "acp"
    }.get(agent_type, agent_type)
    
    # Generate base container name with the new format
    container_name = f"aghub-{agent_type_abbr}-user_{user_id}-id_{deployment.agent_id}-hire_{deployment.hiring_id}-{deployment.deployment_id[:8]}"
    
    # Ensure container name doesn't exceed Docker's 64 character limit
    if len(container_name) > 64:
        # Create a hash of the full deployment_id to ensure uniqueness
        deployment_hash = hashlib.md5(deployment.deployment_id.encode()).hexdigest()
        container_name = f"aghub-{agent_type_abbr}-user_{user_id}-id_{deployment.agent_id}-{deployment_hash[:12]}"
    
    return container_name


def generate_docker_image_name(agent_type: str, user_id: int, agent_id: str, hiring_id: int, deployment_uuid: str) -> str:
    """
    Generate consistent Docker image name for a deployment.
    
    Args:
        agent_type: Type of agent (function, acp, persistent)
        user_id: User ID
        agent_id: Agent ID
        hiring_id: Hiring ID
        deployment_uuid: Deployment UUID
    
    Returns:
        Docker image name in format: {agent_type}_{user_id}_{agent_id}:{hiring_id}_{deployment_uuid}
    """
    # Convert to lowercase and replace hyphens with underscores for Docker compliance
    safe_agent_id = str(agent_id).lower().replace('-', '_')
    safe_deployment_uuid = deployment_uuid.replace('-', '_').lower()
    
    # Format: repository:tag
    # Repository: {agent_type}_{user_id}_{agent_id}
    # Tag: {hiring_id}_{deployment_uuid}
    image_name = f"{agent_type}_{user_id}_{safe_agent_id}:{hiring_id}_{safe_deployment_uuid}"
    
    return image_name
