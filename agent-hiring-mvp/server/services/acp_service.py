"""ACP (Agent Communication Protocol) service."""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.agent import Agent
from ..models.execution import Execution, ExecutionStatus

logger = logging.getLogger(__name__)


class ACPService:
    """Service for managing ACP protocol communication."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def handle_acp_request(self, execution_id: str, acp_message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an ACP request from an agent."""
        execution = self.db.query(Execution).filter(Execution.execution_id == execution_id).first()
        if not execution:
            return {"error": "Execution not found"}
        
        message_type = acp_message.get("type")
        
        if message_type == "start":
            return self._handle_start(execution, acp_message)
        elif message_type == "tool_call":
            return self._handle_tool_call(execution, acp_message)
        elif message_type == "result":
            return self._handle_result(execution, acp_message)
        elif message_type == "error":
            return self._handle_error(execution, acp_message)
        elif message_type == "end":
            return self._handle_end(execution, acp_message)
        else:
            return {"error": f"Unknown message type: {message_type}"}
    
    def _handle_start(self, execution: Execution, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle start message."""
        execution.status = ExecutionStatus.RUNNING.value
        execution.started_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Execution {execution.execution_id} started")
        return {"status": "started"}
    
    def _handle_tool_call(self, execution: Execution, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call message."""
        tool_name = message.get("tool")
        tool_args = message.get("args", {})
        
        # Log the tool call
        logger.info(f"Tool call: {tool_name} with args: {tool_args}")
        
        # For now, we'll simulate tool execution
        # In a real implementation, this would execute the actual tool
        if tool_name is None:
            return {"error": "Tool name is required"}
        
        result = self._simulate_tool_execution(tool_name, tool_args)
        
        return {
            "type": "tool_result",
            "tool": tool_name,
            "result": result
        }
    
    def _handle_result(self, execution: Execution, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle result message."""
        result_data = message.get("result", {})
        
        # Store the result
        execution.output_data = result_data
        execution.status = ExecutionStatus.COMPLETED.value
        execution.completed_at = datetime.utcnow()
        
        if execution.started_at:
            duration = (execution.completed_at - execution.started_at).total_seconds() * 1000
            execution.duration_ms = int(duration)
        
        self.db.commit()
        
        logger.info(f"Execution {execution.execution_id} completed with result")
        return {"status": "result_received"}
    
    def _handle_error(self, execution: Execution, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle error message."""
        error_message = message.get("error", "Unknown error")
        
        execution.status = ExecutionStatus.FAILED.value
        execution.error_message = error_message
        execution.completed_at = datetime.utcnow()
        
        if execution.started_at:
            duration = (execution.completed_at - execution.started_at).total_seconds() * 1000
            execution.duration_ms = int(duration)
        
        self.db.commit()
        
        logger.error(f"Execution {execution.execution_id} failed: {error_message}")
        return {"status": "error_received"}
    
    def _handle_end(self, execution: Execution, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle end message."""
        if execution.status == ExecutionStatus.RUNNING.value:
            execution.status = ExecutionStatus.COMPLETED.value
            execution.completed_at = datetime.utcnow()
            
            if execution.started_at:
                duration = (execution.completed_at - execution.started_at).total_seconds() * 1000
                execution.duration_ms = int(duration)
            
            self.db.commit()
        
        logger.info(f"Execution {execution.execution_id} ended")
        return {"status": "ended"}
    
    def _simulate_tool_execution(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate tool execution for demo purposes."""
        if tool_name == "search":
            query = args.get("query", "")
            return {
                "results": [
                    f"Search result for: {query}",
                    f"Another result for: {query}"
                ]
            }
        elif tool_name == "calculate":
            expression = args.get("expression", "")
            try:
                result = eval(expression)  # Note: In production, use a safer evaluation method
                return {"result": result}
            except Exception as e:
                return {"error": f"Calculation failed: {str(e)}"}
        elif tool_name == "fetch_data":
            url = args.get("url", "")
            return {
                "data": f"Fetched data from {url}",
                "status": "success"
            }
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    def get_acp_status(self, execution_id: str) -> Dict[str, Any]:
        """Get ACP status for an execution."""
        execution = self.db.query(Execution).filter(Execution.execution_id == execution_id).first()
        if not execution:
            return {"error": "Execution not found"}
        
        return {
            "execution_id": execution_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": execution.duration_ms,
            "error_message": execution.error_message,
        }
    
    def create_acp_session(self, agent_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Create a new ACP session."""
        from .execution_service import ExecutionService, ExecutionCreateRequest
        
        execution_service = ExecutionService(self.db)
        execution_data = ExecutionCreateRequest(
            agent_id=agent_id,
            user_id=user_id,
            input_data={"acp_session": True}
        )
        
        execution = execution_service.create_execution(execution_data)
        
        return {
            "session_id": execution.execution_id,
            "agent_id": agent_id,
            "status": "created"
        } 