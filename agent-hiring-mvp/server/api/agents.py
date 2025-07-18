"""Agents API endpoints."""

import logging
import tempfile
import os
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database.config import get_session_dependency
from ..services.agent_service import AgentService, AgentCreateRequest
from ..models.agent import Agent, AgentStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/submit")
async def submit_agent(
    name: str = Form(...),
    description: str = Form(...),
    version: str = Form("1.0.0"),
    author: str = Form(...),
    email: str = Form(...),
    entry_point: str = Form(...),
    requirements: Optional[str] = Form(None),  # JSON string
    config_schema: Optional[str] = Form(None),  # JSON string
    tags: Optional[str] = Form(None),  # JSON string
    category: Optional[str] = Form(None),
    pricing_model: Optional[str] = Form(None),
    price_per_use: Optional[float] = Form(None),
    monthly_price: Optional[float] = Form(None),
    agent_type: Optional[str] = Form("function"),  # New field
    acp_manifest: Optional[str] = Form(None),  # JSON string - New field
    code_file: UploadFile = File(...),
    db: Session = Depends(get_session_dependency),
):
    """Submit a new agent."""
    try:
        # Parse JSON fields
        import json
        requirements_list = json.loads(requirements) if requirements else None
        config_schema_dict = json.loads(config_schema) if config_schema else None
        tags_list = json.loads(tags) if tags else None
        acp_manifest_dict = json.loads(acp_manifest) if acp_manifest else None
        
        # Create agent data
        agent_data = AgentCreateRequest(
            name=name,
            description=description,
            version=version,
            author=author,
            email=email,
            entry_point=entry_point,
            requirements=requirements_list,
            config_schema=config_schema_dict,
            tags=tags_list,
            category=category,
            pricing_model=pricing_model,
            price_per_use=price_per_use,
            monthly_price=monthly_price,
            agent_type=agent_type,
            acp_manifest=acp_manifest_dict,
        )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
            content = await code_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Validate agent code
            agent_service = AgentService(db)
            validation_errors = agent_service.validate_agent_code(temp_file_path)
            
            if validation_errors:
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Agent code validation failed", "errors": validation_errors}
                )
            
            # Create agent
            agent = agent_service.create_agent(agent_data, temp_file_path)
            
            return {
                "message": "Agent submitted successfully",
                "agent_id": agent.id,
                "status": agent.status,
                "agent_type": agent.agent_type,
            }
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in form fields")
    except Exception as e:
        logger.error(f"Error submitting agent: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/")
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    query: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_session_dependency),
):
    """List available agents."""
    agent_service = AgentService(db)
    
    if query or category:
        agents = agent_service.search_agents(query or "", category)
    else:
        agents = agent_service.get_public_agents(skip, limit)
    
    return {
        "agents": [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "author": agent.author,
                "tags": agent.tags,
                "category": agent.category,
                "pricing_model": agent.pricing_model,
                "price_per_use": agent.price_per_use,
                "monthly_price": agent.monthly_price,
                "agent_type": agent.agent_type,
                "status": agent.status,
                "total_hires": agent.total_hires,
                "total_executions": agent.total_executions,
                "average_rating": agent.average_rating,
                "created_at": agent.created_at,
            }
            for agent in agents
        ],
        "total": len(agents),
    }


@router.get("/{agent_id}")
async def get_agent(
    agent_id: int,
    db: Session = Depends(get_session_dependency),
):
    """Get agent details."""
    agent_service = AgentService(db)
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_public or agent.status != AgentStatus.APPROVED.value:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "version": agent.version,
        "author": agent.author,
        "email": agent.email,
        "entry_point": agent.entry_point,
        "requirements": agent.requirements,
        "config_schema": agent.config_schema,
        "tags": agent.tags,
        "category": agent.category,
        "pricing_model": agent.pricing_model,
        "price_per_use": agent.price_per_use,
        "monthly_price": agent.monthly_price,
        "agent_type": agent.agent_type,
        "acp_manifest": agent.acp_manifest,
        "total_hires": agent.total_hires,
        "total_executions": agent.total_executions,
        "average_rating": agent.average_rating,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }


@router.put("/{agent_id}/approve")
async def approve_agent(
    agent_id: int,
    db: Session = Depends(get_session_dependency),
):
    """Approve an agent (admin only)."""
    agent_service = AgentService(db)
    agent = agent_service.approve_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "message": "Agent approved successfully",
        "agent_id": agent.id,
        "status": agent.status,
    }


@router.put("/{agent_id}/reject")
async def reject_agent(
    agent_id: int,
    reason: str,
    db: Session = Depends(get_session_dependency),
):
    """Reject an agent (admin only)."""
    agent_service = AgentService(db)
    agent = agent_service.reject_agent(agent_id, reason)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "message": "Agent rejected",
        "agent_id": agent.id,
        "status": agent.status,
        "reason": reason,
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: Session = Depends(get_session_dependency),
):
    """Delete an agent (admin only)."""
    agent_service = AgentService(db)
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent has active hirings
    if agent.hirings:
        active_hirings = [h for h in agent.hirings if h.status == "active"]
        if active_hirings:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete agent with active hirings"
            )
    
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"} 


@router.get("/{agent_id}/files")
async def get_agent_files(
    agent_id: int,
    db: Session = Depends(get_session_dependency),
):
    """Get all files for an agent."""
    agent_service = AgentService(db)
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_public or agent.status != AgentStatus.APPROVED.value:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get all files for the agent
    files = agent_service.get_agent_files(agent_id)
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "files": files,
        "total_files": len(files)
    }


@router.get("/{agent_id}/files/{file_path:path}")
async def get_agent_file_content(
    agent_id: int,
    file_path: str,
    db: Session = Depends(get_session_dependency),
):
    """Get content of a specific file for an agent."""
    agent_service = AgentService(db)
    agent = agent_service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.is_public or agent.status != AgentStatus.APPROVED.value:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get file content
    file_content = agent_service.get_agent_file_content(agent_id, file_path)
    
    if not file_content:
        raise HTTPException(status_code=404, detail="File not found")
    
    return {
        "agent_id": agent_id,
        "file_path": file_path,
        "content": file_content
    } 