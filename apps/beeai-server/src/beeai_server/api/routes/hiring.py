# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from beeai_server.api.schema.hiring import (
    HireAgentRequest,
    HireAgentResponse,
    AgentPricingResponse,
    TaskStatusResponse,
    CreditsResponse,
)

router = APIRouter(prefix="/hiring", tags=["hiring"])

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
        "completed_tasks": 25,
        "pricing_model": "per_task",
        "price_per_task": Decimal("50.0"),
        "currency": "USD",
        "reliability_score": 4.8,
        "hiring_enabled": True,
        "capabilities": ["Data Analysis", "Visualization", "SQL"],
        "tags": ["data", "analysis", "python"]
    },
    {
        "id": "agent-2",
        "name": "Web Development Agent",
        "description": "Full-stack web development with modern frameworks",
        "skills": ["JavaScript", "React", "Node.js", "Python"],
        "hourly_rate": 75.0,
        "availability": True,
        "rating": 4.9,
        "completed_tasks": 42,
        "pricing_model": "per_task",
        "price_per_task": Decimal("75.0"),
        "currency": "USD",
        "reliability_score": 4.9,
        "hiring_enabled": True,
        "capabilities": ["Web Development", "Frontend", "Backend"],
        "tags": ["web", "development", "javascript"]
    },
    {
        "id": "agent-3",
        "name": "AI/ML Specialist",
        "description": "Expert in machine learning and AI model development",
        "skills": ["Python", "TensorFlow", "PyTorch", "Scikit-learn"],
        "hourly_rate": 100.0,
        "availability": True,
        "rating": 4.7,
        "completed_tasks": 18,
        "pricing_model": "per_task",
        "price_per_task": Decimal("100.0"),
        "currency": "USD",
        "reliability_score": 4.7,
        "hiring_enabled": True,
        "capabilities": ["Machine Learning", "AI", "Model Training"],
        "tags": ["ai", "ml", "python"]
    }
]

MOCK_TASKS = []
MOCK_CREDITS = {"user_credits": Decimal("1000.0")}
TASK_COUNTER = 1


@router.get("/agents", response_model=list[AgentPricingResponse])
async def list_hirable_agents() -> list[AgentPricingResponse]:
    """List all agents that are available for hiring"""
    agents = []
    for agent in MOCK_AGENTS:
        if agent["hiring_enabled"] and agent["availability"]:
            agents.append(
                AgentPricingResponse(
                    agent_name=agent["name"],
                    pricing_model=agent["pricing_model"],
                    price_per_token=Decimal("0.0"),
                    price_per_task=agent["price_per_task"],
                    fixed_price=Decimal("0.0"),
                    currency=agent["currency"],
                    reliability_score=agent["reliability_score"],
                    availability=agent["availability"],
                    hiring_enabled=agent["hiring_enabled"],
                    description=agent["description"],
                    capabilities=agent["capabilities"],
                    tags=agent["tags"],
                )
            )
    return agents


@router.post("/agents/{agent_name}/hire", response_model=HireAgentResponse)
async def hire_agent(agent_name: str, request: HireAgentRequest) -> HireAgentResponse:
    """Hire an agent to perform a task"""
    global TASK_COUNTER
    
    # Find the agent
    agent = None
    for a in MOCK_AGENTS:
        if a["name"] == agent_name:
            agent = a
            break
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found"
        )
    
    if not agent["hiring_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_name}' is not available for hiring"
        )
    
    if not agent["availability"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_name}' is currently unavailable"
        )
    
    # Create task
    task_id = f"task-{TASK_COUNTER}"
    TASK_COUNTER += 1
    
    task = {
        "id": task_id,
        "agent_name": agent_name,
        "status": "pending",
        "input_data": {"task_input": request.task_input},
        "output_data": None,
        "cost": agent["price_per_task"],
        "reliability_score": agent["reliability_score"],
        "error_message": None,
        "created_at": "2025-07-05T19:30:00Z",
        "started_at": None,
        "completed_at": None,
    }
    
    MOCK_TASKS.append(task)
    
    return HireAgentResponse(
        task_id=task_id,
        agent_name=agent_name,
        status="pending",
        estimated_cost=agent["price_per_task"],
        message=f"Task created successfully. Task ID: {task_id}"
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Get the status of a task"""
    task = None
    for t in MOCK_TASKS:
        if t["id"] == task_id:
            task = t
            break
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )
    
    return TaskStatusResponse(
        task_id=task["id"],
        agent_name=task["agent_name"],
        status=task["status"],
        input_data=task["input_data"],
        output_data=task["output_data"],
        cost=task["cost"],
        reliability_score=task["reliability_score"],
        error_message=task["error_message"],
        created_at=task["created_at"],
        started_at=task["started_at"],
        completed_at=task["completed_at"],
    )


@router.get("/credits", response_model=CreditsResponse)
async def get_credits() -> CreditsResponse:
    """Get user credits balance"""
    return CreditsResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000000"),
        balance=MOCK_CREDITS["user_credits"],
        currency="USD",
    )


@router.post("/credits/add")
async def add_credits(request: dict) -> CreditsResponse:
    """Add credits to user account"""
    amount = Decimal(str(request.get("amount", 0.0)))
    MOCK_CREDITS["user_credits"] += amount
    return CreditsResponse(
        user_id=UUID("00000000-0000-0000-0000-000000000000"),
        balance=MOCK_CREDITS["user_credits"],
        currency="USD",
    )


@router.put("/tasks/{task_id}/status")
async def update_task_status(task_id: str, request: dict) -> TaskStatusResponse:
    """Update task status"""
    task = None
    for t in MOCK_TASKS:
        if t["id"] == task_id:
            task = t
            break
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )
    
    status = request.get("status", "pending")
    task["status"] = status
    if status == "in_progress" and not task["started_at"]:
        task["started_at"] = "2025-07-05T19:31:00Z"
    elif status == "completed" and not task["completed_at"]:
        task["completed_at"] = "2025-07-05T19:32:00Z"
    
    return TaskStatusResponse(
        task_id=task["id"],
        agent_name=task["agent_name"],
        status=task["status"],
        input_data=task["input_data"],
        output_data=task["output_data"],
        cost=task["cost"],
        reliability_score=task["reliability_score"],
        error_message=task["error_message"],
        created_at=task["created_at"],
        started_at=task["started_at"],
        completed_at=task["completed_at"],
    )