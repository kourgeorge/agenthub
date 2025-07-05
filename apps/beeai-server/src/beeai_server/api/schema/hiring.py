# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from beeai_server.domain.models.agent import AgentHiringMetadata


class HireAgentRequest(BaseModel):
    """Request to hire an agent"""
    task_input: str = Field(..., description="The task input for the agent")
    task_id: UUID | None = Field(None, description="Optional task ID for tracking")


class HireAgentResponse(BaseModel):
    """Response from hiring an agent"""
    task_id: UUID
    agent_name: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    estimated_cost: Decimal | None = None
    message: str


class AgentPricingResponse(BaseModel):
    """Agent pricing information"""
    agent_name: str
    pricing_model: Literal["fixed", "per_token", "per_task"]
    price_per_token: Decimal | None = None
    price_per_task: Decimal | None = None
    fixed_price: Decimal | None = None
    currency: str
    reliability_score: float
    availability: bool
    hiring_enabled: bool
    description: str | None = None
    capabilities: list[str] = []
    tags: list[str] = []


class TaskStatusResponse(BaseModel):
    """Task status response"""
    task_id: UUID
    agent_name: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    input_data: dict
    output_data: dict | None = None
    cost: Decimal | None = None
    reliability_score: float | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class CreditsResponse(BaseModel):
    """User credits information"""
    user_id: UUID
    balance: Decimal
    currency: str


class UpdateAgentHiringRequest(BaseModel):
    """Request to update agent hiring metadata"""
    hiring_metadata: AgentHiringMetadata 