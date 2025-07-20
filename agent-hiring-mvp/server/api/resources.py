"""Resources API endpoints for agent external resource access."""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.resource_manager import ResourceManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resources", tags=["resources"])


def get_execution_id_from_header(request: Request) -> Optional[str]:
    """Extract execution ID from request headers."""
    return request.headers.get("X-Execution-ID")


def generate_temp_execution_id() -> str:
    """Generate a unique temporary execution ID."""
    return f"temp_{uuid.uuid4().hex}"


@router.post("/llm")
async def llm_completion(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    execution_id: Optional[str] = Depends(get_execution_id_from_header)
):
    """LLM completion endpoint."""
    try:
        # Extract parameters
        provider = request.get("provider", "openai")
        model = request.get("model", "gpt-3.5-turbo")
        messages = request.get("messages", [])
        max_tokens = request.get("max_tokens", 1000)
        temperature = request.get("temperature", 0.7)
        
        # Validate required fields
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Messages are required"
            )
        
        # Create resource manager
        resource_manager = ResourceManager(db)
        
        # Get resource proxy for this execution
        if execution_id:
            resource_proxy = resource_manager.get_proxy(execution_id)
        else:
            # Use temporary execution ID without database record
            temp_execution_id = generate_temp_execution_id()
            resource_proxy = resource_manager.get_proxy(temp_execution_id)
        
        # Call LLM
        response = await resource_proxy.llm_complete(
            provider=provider,
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return {
            "success": True,
            "content": response,
            "provider": provider,
            "model": model,
            "execution_id": execution_id or temp_execution_id
        }
        
    except Exception as e:
        logger.error(f"LLM completion error: {e}")
        return {
            "success": False,
            "error": str(e),
            "execution_id": execution_id
        }


@router.post("/web_search")
async def web_search(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    execution_id: Optional[str] = Depends(get_execution_id_from_header)
):
    """Web search endpoint."""
    try:
        # Extract parameters
        query = request.get("query", "")
        provider = request.get("provider", "serper")
        num_results = request.get("num_results", 5)
        
        # Validate required fields
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )
        
        # Create resource manager
        resource_manager = ResourceManager(db)
        
        # Get resource proxy for this execution
        if execution_id:
            resource_proxy = resource_manager.get_proxy(execution_id)
        else:
            # Use temporary execution ID without database record
            temp_execution_id = generate_temp_execution_id()
            resource_proxy = resource_manager.get_proxy(temp_execution_id)
        
        # Call web search
        results = await resource_proxy.web_search(
            query=query,
            provider=provider,
            num_results=num_results
        )
        
        return {
            "success": True,
            "results": results,
            "provider": provider,
            "query": query,
            "execution_id": execution_id or temp_execution_id
        }
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "execution_id": execution_id
        }


@router.post("/vector_db")
async def vector_db_operation(
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    execution_id: Optional[str] = Depends(get_execution_id_from_header)
):
    """Vector database operations endpoint."""
    try:
        # Extract parameters
        operation = request.get("operation", "search")
        provider = request.get("provider", "pinecone")
        collection_name = request.get("collection_name", "")
        query_text = request.get("query_text", "")
        documents = request.get("documents", [])
        
        # Validate required fields
        if operation == "search" and not query_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query text is required for search operation"
            )
        elif operation == "add" and not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Documents are required for add operation"
            )
        
        # Create resource manager
        resource_manager = ResourceManager(db)
        
        # Get resource proxy for this execution
        if execution_id:
            resource_proxy = resource_manager.get_proxy(execution_id)
        else:
            # Use temporary execution ID without database record
            temp_execution_id = generate_temp_execution_id()
            resource_proxy = resource_manager.get_proxy(temp_execution_id)
        
        # Call vector database operation
        if operation == "search":
            # For now, we'll need to generate embeddings first
            # This is a simplified version - in production you'd want proper embedding generation
            dummy_vector = [0.1] * 1536  # OpenAI embedding dimension
            results = await resource_proxy.vector_search(
                query_vector=dummy_vector,
                provider=provider
            )
        elif operation == "add":
            # Vector add operation not implemented in proxy yet
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Vector add operation not yet implemented"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported operation: {operation}"
            )
        
        return {
            "success": True,
            "results": results,
            "provider": provider,
            "operation": operation,
            "execution_id": execution_id or temp_execution_id
        }
        
    except Exception as e:
        logger.error(f"Vector DB operation error: {e}")
        return {
            "success": False,
            "error": str(e),
            "execution_id": execution_id
        }


@router.get("/health")
async def resources_health():
    """Health check for resources API."""
    return {
        "status": "healthy",
        "service": "resources-api",
        "endpoints": {
            "llm": "/api/v1/resources/llm",
            "web_search": "/api/v1/resources/web_search",
            "vector_db": "/api/v1/resources/vector_db"
        }
    } 