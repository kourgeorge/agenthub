"""Agent proxy API endpoints for communicating with deployed ACP agents."""

import json
import aiohttp
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.deployment import AgentDeployment, DeploymentStatus
from ..models.hiring import Hiring

router = APIRouter(prefix="/agent-proxy", tags=["agent-proxy"])


@router.post("/chat/{hiring_id}")
async def chat_with_agent(
    hiring_id: int,
    message: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Send a message to a deployed ACP agent."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Check if deployment is running
    if deployment.status != DeploymentStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent deployment is not running. Status: {deployment.status}"
        )
    
    # Check if agent is healthy
    if not deployment.is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent is not healthy"
        )
    
    # Forward message to the ACP agent
    try:
        async with aiohttp.ClientSession() as session:
            agent_url = f"{deployment.proxy_endpoint}/chat"
            
            async with session.post(
                agent_url,
                json=message,
                timeout=aiohttp.ClientTimeout(total=30)
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
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Agent returned error: {error_text}"
                    )
    
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to communicate with agent: {str(e)}"
        )


@router.post("/message/{hiring_id}")
async def send_message_to_agent(
    hiring_id: int,
    message: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Send a generic message to a deployed ACP agent."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Check if deployment is running
    if deployment.status != DeploymentStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent deployment is not running. Status: {deployment.status}"
        )
    
    # Forward message to the ACP agent
    try:
        async with aiohttp.ClientSession() as session:
            agent_url = f"{deployment.proxy_endpoint}/message"
            
            async with session.post(
                agent_url,
                json=message,
                timeout=aiohttp.ClientTimeout(total=60)
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
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Agent returned error: {error_text}"
                    )
    
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to communicate with agent: {str(e)}"
        )


@router.get("/info/{hiring_id}")
async def get_agent_info(
    hiring_id: int,
    db: Session = Depends(get_db)
):
    """Get information about a deployed ACP agent."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Get agent info from the ACP agent
    try:
        async with aiohttp.ClientSession() as session:
            agent_url = f"{deployment.proxy_endpoint}/info"
            
            async with session.get(
                agent_url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    agent_info = await response.json()
                    return {
                        "agent_info": agent_info,
                        "deployment_info": {
                            "deployment_id": deployment.deployment_id,
                            "status": deployment.status,
                            "proxy_endpoint": deployment.proxy_endpoint,
                            "is_healthy": deployment.is_healthy,
                            "created_at": deployment.created_at.isoformat()
                        },
                        "hiring_id": hiring_id
                    }
                else:
                    return {
                        "agent_info": {"error": "Unable to fetch agent info"},
                        "deployment_info": {
                            "deployment_id": deployment.deployment_id,
                            "status": deployment.status,
                            "proxy_endpoint": deployment.proxy_endpoint,
                            "is_healthy": deployment.is_healthy,
                            "created_at": deployment.created_at.isoformat()
                        },
                        "hiring_id": hiring_id
                    }
    
    except aiohttp.ClientError:
        return {
            "agent_info": {"error": "Unable to connect to agent"},
            "deployment_info": {
                "deployment_id": deployment.deployment_id,
                "status": deployment.status,
                "proxy_endpoint": deployment.proxy_endpoint,
                "is_healthy": deployment.is_healthy,
                "created_at": deployment.created_at.isoformat()
            },
            "hiring_id": hiring_id
        }


@router.get("/endpoint/{hiring_id}")
def get_agent_endpoint(
    hiring_id: int,
    db: Session = Depends(get_db)
):
    """Get the communication endpoint for a hired agent."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Get hiring info
    hiring = db.query(Hiring).filter(Hiring.id == hiring_id).first()
    
    return {
        "hiring_id": hiring_id,
        "agent_id": deployment.agent_id,
        "agent_name": hiring.agent.name if hiring else "Unknown",
        "deployment_id": deployment.deployment_id,
        "endpoints": {
            "chat": f"/api/v1/agent-proxy/chat/{hiring_id}",
            "message": f"/api/v1/agent-proxy/message/{hiring_id}",
            "info": f"/api/v1/agent-proxy/info/{hiring_id}",
            "direct_proxy": deployment.proxy_endpoint
        },
        "status": deployment.status,
        "is_healthy": deployment.is_healthy,
        "created_at": deployment.created_at.isoformat()
    }


@router.api_route("/{hiring_id}/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(
    hiring_id: int,
    path: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Proxy any request directly to the deployed ACP agent."""
    
    # Get the deployment for this hiring
    deployment = db.query(AgentDeployment).filter(
        AgentDeployment.hiring_id == hiring_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment found for this hiring"
        )
    
    # Check if deployment is running
    if deployment.status != DeploymentStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent deployment is not running. Status: {deployment.status}"
        )
    
    # Proxy the request
    try:
        async with aiohttp.ClientSession() as session:
            agent_url = f"{deployment.proxy_endpoint}/{path}"
            
            # Get request body if present
            body = None
            if request.method in ["POST", "PUT"]:
                body = await request.body()
            
            # Forward request to agent
            async with session.request(
                method=request.method,
                url=agent_url,
                data=body,
                headers={
                    key: value for key, value in request.headers.items()
                    if key.lower() not in ["host", "content-length"]
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                
                # Return response
                content = await response.read()
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "content": content.decode() if content else None,
                    "deployment_id": deployment.deployment_id
                }
    
    except aiohttp.ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to proxy request to agent: {str(e)}"
        ) 