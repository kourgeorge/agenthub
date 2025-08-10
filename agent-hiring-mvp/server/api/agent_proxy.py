"""Agent proxy API endpoints for communicating with deployed ACP agents."""

import json
import io
import logging
import aiohttp
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.deployment import AgentDeployment, DeploymentStatus
from ..models.hiring import Hiring
from ..middleware.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-proxy", tags=["agent-proxy"])


async def _validate_deployment_access(
    hiring_id: int, 
    current_user, 
    db: Session
) -> tuple[AgentDeployment, Hiring]:
    """Validate deployment access and return deployment and hiring objects."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Get the hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure the user can only access their own hirings
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own hirings"
        )
    
    # Check if deployment is running
    if deployment.status != DeploymentStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent deployment is not running. Status: {deployment.status}"
        )
    
    return deployment, hiring


async def _make_agent_request(
    deployment: AgentDeployment,
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """Make a request to the ACP agent with proper error handling."""
    
    try:
        async with aiohttp.ClientSession() as session:
            agent_url = f"{deployment.proxy_endpoint}/{endpoint}"
            
            async with session.request(
                method=method,
                url=agent_url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "response": result,
                        "deployment_id": deployment.deployment_id,
                        "agent_id": deployment.agent_id,
                        "status": "success"
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Agent returned error {response.status}: {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Agent returned error: {error_text}"
                    )
    
    except aiohttp.ClientError as e:
        logger.error(f"Failed to communicate with agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to communicate with agent: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error communicating with agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/chat/{hiring_id}")
async def chat_with_agent(
    hiring_id: int,
    message: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a chat message to a deployed ACP agent."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    # Check if agent is healthy
    if not deployment.is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent is not healthy"
        )
    
    logger.info(f"User {current_user.id} sending chat message to agent {deployment.agent_id}")
    return await _make_agent_request(deployment, "POST", "chat", message, timeout=30)


@router.post("/message/{hiring_id}")
async def send_message_to_agent(
    hiring_id: int,
    message: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a deployed ACP agent."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    logger.info(f"User {current_user.id} sending message to agent {deployment.agent_id}")
    return await _make_agent_request(deployment, "POST", "message", message, timeout=60)


@router.get("/info/{hiring_id}")
async def get_agent_info(
    hiring_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get information about a deployed ACP agent."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    logger.info(f"User {current_user.id} requesting info for agent {deployment.agent_id}")
    return await _make_agent_request(deployment, "GET", "info", timeout=10)


@router.get("/health/{hiring_id}")
async def check_agent_health(
    hiring_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check the health status of a deployed ACP agent."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    try:
        async with aiohttp.ClientSession() as session:
            agent_url = f"{deployment.proxy_endpoint}/health"
            
            async with session.get(
                agent_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    health_data = await response.json()
                    return {
                        "deployment_id": deployment.deployment_id,
                        "agent_id": deployment.agent_id,
                        "status": "healthy",
                        "health_data": health_data,
                        "deployment_healthy": deployment.is_healthy
                    }
                else:
                    return {
                        "deployment_id": deployment.deployment_id,
                        "agent_id": deployment.agent_id,
                        "status": "unhealthy",
                        "deployment_healthy": deployment.is_healthy,
                        "error": f"Agent health check failed with status {response.status}"
                    }
    
    except Exception as e:
        logger.error(f"Health check failed for agent {deployment.agent_id}: {str(e)}")
        return {
            "deployment_id": deployment.deployment_id,
            "agent_id": deployment.agent_id,
            "status": "unhealthy",
            "deployment_healthy": deployment.is_healthy,
            "error": f"Health check failed: {str(e)}"
        }


@router.get("/endpoint/{hiring_id}")
def get_agent_endpoint(
    hiring_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the endpoint information for a deployed ACP agent."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Get the hiring to check user ownership
    hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
    if not hiring:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiring not found"
        )
    
    # Ensure the user can only access their own hirings
    if hiring.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only access your own hirings"
        )
    
    return {
        "deployment_id": deployment.deployment_id,
        "agent_id": deployment.agent_id,
        "proxy_endpoint": deployment.proxy_endpoint,
        "status": deployment.status,
        "is_healthy": deployment.is_healthy,
        "created_at": deployment.created_at,
        "updated_at": deployment.updated_at
    }


@router.api_route("/{hiring_id}/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(
    hiring_id: int,
    path: str,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """General proxy endpoint for forwarding requests to ACP agents.
    This provides a flexible way to access any endpoint on the agent."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    logger.info(f"User {current_user.id} proxying request to {path} on agent {deployment.agent_id}")
    
    # Proxy the request
    try:
        async with aiohttp.ClientSession() as session:
            # Construct the target URL with the path
            target_url = f"{deployment.proxy_endpoint}/{path}"
            
            # Get request body if present
            body = None
            if request.method in ["POST", "PUT"]:
                body = await request.body()
            
            # Forward request to agent
            async with session.request(
                method=request.method,
                url=target_url,
                data=body,
                headers={
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ["host", "content-length"]
                },
                params=dict(request.query_params),
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                # Return the response directly
                content = await response.read()
                
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=response.headers.get("content-type", "application/json"),
                    headers=dict(response.headers)
                )
    
    except aiohttp.ClientError as e:
        logger.error(f"Proxy request failed for agent {deployment.agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to proxy request to agent: {str(e)}"
        )


@router.api_route("/{hiring_id}/acp", methods=["GET", "POST", "PUT", "DELETE"])
async def acp_proxy_root(
    hiring_id: int,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ACP proxy root endpoint - forwards requests to the ACP agent container root."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    logger.info(f"User {current_user.id} accessing ACP root on agent {deployment.agent_id}")
    
    # Proxy the request
    try:
        async with aiohttp.ClientSession() as session:
            # Get request body if present
            body = None
            if request.method in ["POST", "PUT"]:
                body = await request.body()
            
            # Forward request to agent root
            async with session.request(
                method=request.method,
                url=deployment.proxy_endpoint,
                data=body,
                headers={
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ["host", "content-length"]
                },
                params=dict(request.query_params),
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                # Return the response directly
                content = await response.read()
                
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=response.headers.get("content-type", "application/json"),
                    headers=dict(response.headers)
                )
    
    except aiohttp.ClientError as e:
        logger.error(f"ACP root proxy failed for agent {deployment.agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to proxy request to agent: {str(e)}"
        )


@router.api_route("/{hiring_id}/acp/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def acp_proxy(
    hiring_id: int,
    path: str,
    request: Request,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Simple ACP proxy - forwards everything directly to the ACP agent container.
    This is like a port mapping/forwarding service."""
    
    deployment, hiring = await _validate_deployment_access(hiring_id, current_user, db)
    
    logger.info(f"User {current_user.id} accessing ACP path {path} on agent {deployment.agent_id}")
    
    # Proxy the request
    try:
        async with aiohttp.ClientSession() as session:
            # Construct the target URL with the path
            target_url = f"{deployment.proxy_endpoint}/{path}"
            
            # Get request body if present
            body = None
            if request.method in ["POST", "PUT"]:
                body = await request.body()
            
            # Forward request to agent with minimal processing
            async with session.request(
                method=request.method,
                url=target_url,
                data=body,
                headers={
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ["host", "content-length"]
                },
                params=dict(request.query_params),
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                # Return the response directly (like a true proxy)
                content = await response.read()
                
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type=response.headers.get("content-type", "application/json"),
                    headers=dict(response.headers)
                )
    
    except aiohttp.ClientError as e:
        logger.error(f"ACP proxy failed for agent {deployment.agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to proxy request to agent: {str(e)}"
        ) 