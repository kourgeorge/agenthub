# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from uuid import UUID, uuid4
from typing import Literal
from decimal import Decimal

from pydantic import BaseModel, Field, AwareDatetime

from acp_sdk.models import AgentManifest as AcpAgentOriginal, Metadata as AcpMetadataOriginal

from beeai_server.utils.utils import utc_now


class EnvVar(BaseModel):
    name: str
    description: str | None = None
    required: bool = False


class AcpMetadata(AcpMetadataOriginal):
    env: list[EnvVar] = Field(default_factory=list, description="For configuration -- passed to the process")
    provider_id: UUID


class AgentHiringMetadata(BaseModel):
    """Hiring metadata for agents in the AI Agent Hiring System"""
    pricing_model: Literal["fixed", "per_token", "per_task"] = "fixed"
    price_per_token: Decimal = Field(default=Decimal("0.0"), description="Price per token for per_token pricing")
    price_per_task: Decimal = Field(default=Decimal("0.0"), description="Price per task for per_task pricing")
    fixed_price: Decimal = Field(default=Decimal("0.0"), description="Fixed price for fixed pricing")
    currency: str = Field(default="USD", description="Currency for pricing")
    availability: bool = Field(default=True, description="Whether the agent is available for hiring")
    reliability_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Reliability score (0-100)")
    creator_api_key: str | None = Field(default=None, description="API key of the agent creator")
    creator_id: UUID | None = Field(default=None, description="ID of the agent creator")
    hiring_enabled: bool = Field(default=False, description="Whether hiring is enabled for this agent")
    max_concurrent_tasks: int = Field(default=1, ge=1, description="Maximum concurrent tasks this agent can handle")
    task_timeout_seconds: int = Field(default=300, ge=60, description="Task timeout in seconds")
    description: str | None = Field(default=None, description="Hiring-specific description")
    capabilities: list[str] = Field(default_factory=list, description="List of agent capabilities")
    tags: list[str] = Field(default_factory=list, description="Tags for agent discovery")


class Agent(AcpAgentOriginal, extra="allow"):
    id: UUID = Field(default_factory=uuid4)
    metadata: AcpMetadata
    hiring_metadata: AgentHiringMetadata | None = Field(default=None, description="Hiring metadata for this agent")

    @property
    def provider_id(self):
        return self.metadata.provider_id


class AgentRunRequest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    acp_run_id: UUID | None = None
    acp_session_id: UUID | None = None
    agent_id: UUID
    created_at: AwareDatetime = Field(default_factory=utc_now)
    finished_at: AwareDatetime | None = None
    created_by: UUID

    def set_finished(self):
        self.finished_at = utc_now()


class Task(BaseModel):
    """Task model for the AI Agent Hiring System"""
    id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    client_id: UUID
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    input_data: dict = Field(default_factory=dict)
    output_data: dict | None = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    cost: Decimal | None = None
    reliability_score: float | None = None
    error_message: str | None = None
    created_at: AwareDatetime = Field(default_factory=utc_now)
    updated_at: AwareDatetime = Field(default_factory=utc_now)

    def start(self):
        self.status = "running"
        self.started_at = utc_now()
        self.updated_at = utc_now()

    def complete(self, output_data: dict, cost: Decimal | None = None, reliability_score: float | None = None):
        self.status = "completed"
        self.output_data = output_data
        self.completed_at = utc_now()
        self.cost = cost
        self.reliability_score = reliability_score
        self.updated_at = utc_now()

    def fail(self, error_message: str):
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = utc_now()
        self.updated_at = utc_now()

    def cancel(self):
        self.status = "cancelled"
        self.completed_at = utc_now()
        self.updated_at = utc_now()


class Credits(BaseModel):
    """Credits model for the AI Agent Hiring System"""
    user_id: UUID
    balance: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    currency: str = Field(default="USD")
    created_at: AwareDatetime = Field(default_factory=utc_now)
    updated_at: AwareDatetime = Field(default_factory=utc_now)

    def add_credits(self, amount: Decimal):
        self.balance += amount
        self.updated_at = utc_now()

    def deduct_credits(self, amount: Decimal) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            self.updated_at = utc_now()
            return True
        return False
