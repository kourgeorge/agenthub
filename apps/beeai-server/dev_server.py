#!/usr/bin/env python3
"""
Development server for testing the hiring system without database dependencies.
This is a simplified version for local development and testing.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Iterable

from fastapi import FastAPI, APIRouter
from fastapi.responses import ORJSONResponse
from starlette.requests import Request
from starlette.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock data for development
MOCK_AGENTS = [
    {
        "id": "agent-1",
        "name": "Data Analysis Agent",
        "description": "Specialized in data analysis and visualization",
        "skills": ["Python", "Pandas", "Matplotlib", "SQL"],
        "hourly_rate": 50.0,
        "availability": True,
        "rating": 4.8,
        "completed_tasks": 25
    },
    {
        "id": "agent-2", 
        "name": "Web Development Agent",
        "description": "Full-stack web development with modern frameworks",
        "skills": ["JavaScript", "React", "Node.js", "Python", "Django"],
        "hourly_rate": 75.0,
        "availability": True,
        "rating": 4.9,
        "completed_tasks": 42
    },
    {
        "id": "agent-3",
        "name": "AI/ML Specialist",
        "description": "Machine learning and AI model development",
        "skills": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "NLP"],
        "hourly_rate": 100.0,
        "availability": False,
        "rating": 4.7,
        "completed_tasks": 18
    }
]

MOCK_TASKS = []
MOCK_CREDITS = {"user_credits": 1000.0}

# Create FastAPI app
app = FastAPI(
    title="BeeAI Hiring System - Development Server",
    description="Development server for testing the AI Agent Hiring System",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Create routers
hiring_router = APIRouter()

@hiring_router.get("/agents")
async def list_agents():
    """List all available agents"""
    return {"agents": MOCK_AGENTS}

@hiring_router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    agent = next((a for a in MOCK_AGENTS if a["id"] == agent_id), None)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return {"agent": agent}

@hiring_router.post("/tasks")
async def create_task(request: Request):
    """Create a new task"""
    data = await request.json()
    task_id = f"task-{len(MOCK_TASKS) + 1}"
    task = {
        "id": task_id,
        "title": data.get("title", "Untitled Task"),
        "description": data.get("description", ""),
        "agent_id": data.get("agent_id"),
        "budget": data.get("budget", 0.0),
        "status": "pending",
        "created_at": "2025-01-05T19:30:00Z"
    }
    MOCK_TASKS.append(task)
    return {"task": task}

@hiring_router.get("/tasks")
async def list_tasks():
    """List all tasks"""
    return {"tasks": MOCK_TASKS}

@hiring_router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details"""
    task = next((t for t in MOCK_TASKS if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    return {"task": task}

@hiring_router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, request: Request):
    """Update task status"""
    data = await request.json()
    task = next((t for t in MOCK_TASKS if t["id"] == task_id), None)
    if not task:
        return JSONResponse({"error": "Task not found"}, status_code=404)
    
    task["status"] = data.get("status", task["status"])
    return {"task": task}

@hiring_router.get("/credits")
async def get_credits():
    """Get user credits"""
    return {"credits": MOCK_CREDITS}

@hiring_router.post("/credits/add")
async def add_credits(request: Request):
    """Add credits to user account"""
    data = await request.json()
    amount = data.get("amount", 0.0)
    MOCK_CREDITS["user_credits"] += amount
    return {"credits": MOCK_CREDITS}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "beeai-hiring-dev"}

# Mount hiring routes
app.include_router(hiring_router, prefix="/api/v1/hiring", tags=["hiring"])

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting BeeAI Hiring System Development Server")
    print("📖 API Documentation: http://localhost:8001/docs")
    print("🔗 Health Check: http://localhost:8001/health")
    print("🤖 Hiring API: http://localhost:8001/api/v1/hiring")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "dev_server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 