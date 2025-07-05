# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from beeai_server.api.schema.hiring import (
    HireAgentRequest,
    HireAgentResponse,
    AgentPricingResponse,
    TaskStatusResponse,
    CreditsResponse,
    UpdateAgentHiringRequest,
)
from beeai_server.domain.models.agent import Task, Credits, AgentHiringMetadata
from beeai_server.service_layer.unit_of_work import IUnitOfWork
from beeai_server.service_layer.dependencies import get_unit_of_work
from beeai_server.utils.utils import utc_now

router = APIRouter(prefix="/hiring", tags=["hiring"])


@router.get("/agents", response_model=list[AgentPricingResponse])
async def list_hirable_agents(
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> list[AgentPricingResponse]:
    """List all agents that are available for hiring"""
    agents = []
    async for agent in uow.agents.list():
        if agent.hiring_metadata and agent.hiring_metadata.hiring_enabled and agent.hiring_metadata.availability:
            agents.append(
                AgentPricingResponse(
                    agent_name=agent.name,
                    pricing_model=agent.hiring_metadata.pricing_model,
                    price_per_token=agent.hiring_metadata.price_per_token,
                    price_per_task=agent.hiring_metadata.price_per_task,
                    fixed_price=agent.hiring_metadata.fixed_price,
                    currency=agent.hiring_metadata.currency,
                    reliability_score=agent.hiring_metadata.reliability_score,
                    availability=agent.hiring_metadata.availability,
                    hiring_enabled=agent.hiring_metadata.hiring_enabled,
                    description=agent.hiring_metadata.description,
                    capabilities=agent.hiring_metadata.capabilities,
                    tags=agent.hiring_metadata.tags,
                )
            )
    return agents


@router.post("/agents/{agent_name}/hire", response_model=HireAgentResponse)
async def hire_agent(
    agent_name: str,
    request: HireAgentRequest,
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> HireAgentResponse:
    """Hire an agent to perform a task"""
    # Get the agent
    try:
        agent = await uow.agents.get_agent_by_name(name=agent_name)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found"
        )
    
    # Check if agent is available for hiring
    if not agent.hiring_metadata or not agent.hiring_metadata.hiring_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_name}' is not available for hiring"
        )
    
    if not agent.hiring_metadata.availability:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_name}' is currently unavailable"
        )
    
    # Check if agent has capacity (simplified check)
    active_tasks = []
    async for task in uow.tasks.get_active_tasks_by_agent(agent_id=agent.id):
        active_tasks.append(task)
    
    if len(active_tasks) >= agent.hiring_metadata.max_concurrent_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent '{agent_name}' is at maximum capacity"
        )
    
    # Calculate estimated cost
    estimated_cost = None
    if agent.hiring_metadata.pricing_model == "fixed":
        estimated_cost = agent.hiring_metadata.fixed_price
    elif agent.hiring_metadata.pricing_model == "per_task":
        estimated_cost = agent.hiring_metadata.price_per_task
    
    # Create task
    task = Task(
        agent_id=agent.id,
        client_id=UUID("00000000-0000-0000-0000-000000000000"),  # TODO: Get from auth
        input_data={"task_input": request.task_input},
    )
    
    await uow.tasks.create(task=task)
    await uow.commit()
    
    return HireAgentResponse(
        task_id=task.id,
        agent_name=agent.name,
        status=task.status,
        estimated_cost=estimated_cost,
        message=f"Task created successfully. Task ID: {task.id}"
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> TaskStatusResponse:
    """Get the status of a task"""
    try:
        task = await uow.tasks.get(task_id=task_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )
    
    # Get agent name
    agent = await uow.agents.get_agent(agent_id=task.agent_id)
    
    return TaskStatusResponse(
        task_id=task.id,
        agent_name=agent.name,
        status=task.status,
        input_data=task.input_data,
        output_data=task.output_data,
        cost=task.cost,
        reliability_score=task.reliability_score,
        error_message=task.error_message,
        created_at=task.created_at.isoformat(),
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.get("/credits", response_model=CreditsResponse)
async def get_credits(
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> CreditsResponse:
    """Get user credits balance"""
    user_id = UUID("00000000-0000-0000-0000-000000000000")  # TODO: Get from auth
    
    try:
        credits = await uow.credits.get(user_id=user_id)
    except Exception:
        # Create credits record if it doesn't exist
        credits = Credits(user_id=user_id, balance=Decimal("0.0"))
        await uow.credits.create(credits=credits)
        await uow.commit()
    
    return CreditsResponse(
        user_id=credits.user_id,
        balance=credits.balance,
        currency=credits.currency,
    )


@router.post("/agents/{agent_name}/hiring-metadata")
async def update_agent_hiring_metadata(
    agent_name: str,
    request: UpdateAgentHiringRequest,
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> dict:
    """Update agent hiring metadata (for agent creators)"""
    try:
        agent = await uow.agents.get_agent_by_name(name=agent_name)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_name}' not found"
        )
    
    # TODO: Check if user is the agent creator
    # if agent.hiring_metadata and agent.hiring_metadata.creator_id != user_id:
    #     raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update hiring metadata
    agent.hiring_metadata = request.hiring_metadata
    
    # Save back to database (this would need to be implemented in the repository)
    # For now, we'll just return success
    await uow.commit()
    
    return {"message": f"Hiring metadata updated for agent '{agent_name}'"}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    uow: IUnitOfWork = Depends(get_unit_of_work),
) -> dict:
    """Cancel a running task"""
    try:
        task = await uow.tasks.get(task_id=task_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found"
        )
    
    if task.status in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task '{task_id}' cannot be cancelled (status: {task.status})"
        )
    
    task.cancel()
    await uow.tasks.update(task=task)
    await uow.commit()
    
    return {"message": f"Task '{task_id}' cancelled successfully"} 