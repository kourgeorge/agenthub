"""ACP (Agent Communication Protocol) API endpoints."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.acp_service import ACPService

router = APIRouter(prefix="/acp", tags=["acp"])


@router.get("/discovery")
def acp_discovery():
    """ACP protocol discovery endpoint."""
    return {
        "protocol": "ACP",
        "version": "1.0.0",
        "name": "Agent Communication Protocol",
        "description": "Standard protocol for agent communication"
    }


@router.get("/capabilities")
def acp_capabilities():
    """ACP protocol capabilities endpoint."""
    return {
        "capabilities": [
            "session_management",
            "message_routing",
            "tool_calling",
            "result_submission",
            "error_handling",
            "execution_control"
        ],
        "supported_versions": ["1.0.0"],
        "features": {
            "async_execution": True,
            "tool_integration": True,
            "state_management": True
        }
    }


@router.post("/session")
def create_acp_session(
    agent_id: int,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Create a new ACP session."""
    acp_service = ACPService(db)
    session = acp_service.create_acp_session(agent_id, user_id)
    
    return {
        "session_id": session["session_id"],
        "agent_id": session["agent_id"],
        "status": session["status"],
        "message": "ACP session created successfully"
    }


@router.post("/{execution_id}/message")
def handle_acp_message(
    execution_id: str,
    message: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Handle an ACP message from an agent."""
    acp_service = ACPService(db)
    result = acp_service.handle_acp_request(execution_id, message)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.get("/{execution_id}/status")
def get_acp_status(execution_id: str, db: Session = Depends(get_db)):
    """Get ACP status for an execution."""
    acp_service = ACPService(db)
    status_info = acp_service.get_acp_status(execution_id)
    
    if "error" in status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=status_info["error"]
        )
    
    return status_info


@router.post("/{execution_id}/start")
def start_execution(execution_id: str, db: Session = Depends(get_db)):
    """Start an ACP execution."""
    acp_service = ACPService(db)
    result = acp_service.handle_acp_request(execution_id, {"type": "start"})
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/{execution_id}/tool")
def call_tool(
    execution_id: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Call a tool via ACP."""
    acp_service = ACPService(db)
    result = acp_service.handle_acp_request(execution_id, {
        "type": "tool_call",
        "tool": tool_name,
        "args": tool_args
    })
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/{execution_id}/result")
def submit_result(
    execution_id: str,
    result_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Submit execution result via ACP."""
    acp_service = ACPService(db)
    result = acp_service.handle_acp_request(execution_id, {
        "type": "result",
        "result": result_data
    })
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/{execution_id}/error")
def submit_error(
    execution_id: str,
    error_message: str,
    db: Session = Depends(get_db)
):
    """Submit execution error via ACP."""
    acp_service = ACPService(db)
    result = acp_service.handle_acp_request(execution_id, {
        "type": "error",
        "error": error_message
    })
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/{execution_id}/end")
def end_execution(execution_id: str, db: Session = Depends(get_db)):
    """End an ACP execution."""
    acp_service = ACPService(db)
    result = acp_service.handle_acp_request(execution_id, {"type": "end"})
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result 