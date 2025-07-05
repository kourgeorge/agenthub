# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import Table, Column, String, JSON, ForeignKey, UUID as SqlUUID, Text, Select, Row, DateTime, Numeric, Float, Enum
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import select, insert, delete, update

from beeai_server.domain.models.agent import Task
from beeai_server.domain.repositories.task import ITaskRepository
from beeai_server.exceptions import EntityNotFoundError, DuplicateEntityError
from beeai_server.infrastructure.persistence.repositories.db_metadata import metadata
from beeai_server.utils.utils import utc_now

tasks_table = Table(
    "tasks",
    metadata,
    Column("id", SqlUUID, primary_key=True),
    Column("agent_id", ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
    Column("client_id", ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("status", Enum("pending", "running", "completed", "failed", "cancelled", name="task_status"), nullable=False),
    Column("input_data", JSON, nullable=False),
    Column("output_data", JSON, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("completed_at", DateTime(timezone=True), nullable=True),
    Column("cost", Numeric(10, 2), nullable=True),
    Column("reliability_score", Float, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class SqlAlchemyTaskRepository(ITaskRepository):
    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def create(self, task: Task) -> None:
        query = insert(tasks_table).values(
            id=task.id,
            agent_id=task.agent_id,
            client_id=task.client_id,
            status=task.status,
            input_data=task.input_data,
            output_data=task.output_data,
            started_at=task.started_at,
            completed_at=task.completed_at,
            cost=task.cost,
            reliability_score=task.reliability_score,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        try:
            await self.connection.execute(query)
        except IntegrityError:
            raise DuplicateEntityError(entity="task", field="id", value=str(task.id))

    async def get(self, *, task_id: UUID) -> Task:
        return await self._get_one(tasks_table.select().where(tasks_table.c.id == task_id), id=task_id)

    async def list_by_agent(self, *, agent_id: UUID) -> AsyncIterator[Task]:
        query = tasks_table.select().where(tasks_table.c.agent_id == agent_id)
        async for row in await self.connection.stream(query):
            yield self._to_task(row)

    async def list_by_client(self, *, client_id: UUID) -> AsyncIterator[Task]:
        query = tasks_table.select().where(tasks_table.c.client_id == client_id)
        async for row in await self.connection.stream(query):
            yield self._to_task(row)

    async def update(self, *, task: Task) -> None:
        query = (
            tasks_table.update()
            .where(tasks_table.c.id == task.id)
            .values(
                status=task.status,
                input_data=task.input_data,
                output_data=task.output_data,
                started_at=task.started_at,
                completed_at=task.completed_at,
                cost=task.cost,
                reliability_score=task.reliability_score,
                error_message=task.error_message,
                updated_at=task.updated_at,
            )
        )
        await self.connection.execute(query)

    async def delete(self, *, task_id: UUID) -> None:
        query = delete(tasks_table).where(tasks_table.c.id == task_id)
        await self.connection.execute(query)

    async def get_active_tasks_by_agent(self, *, agent_id: UUID) -> AsyncIterator[Task]:
        query = tasks_table.select().where(
            tasks_table.c.agent_id == agent_id,
            tasks_table.c.status.in_(["pending", "running"])
        )
        async for row in await self.connection.stream(query):
            yield self._to_task(row)

    def _to_task(self, row: Row) -> Task:
        return Task.model_validate(
            {
                "id": row.id,
                "agent_id": row.agent_id,
                "client_id": row.client_id,
                "status": row.status,
                "input_data": row.input_data,
                "output_data": row.output_data,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "cost": row.cost,
                "reliability_score": row.reliability_score,
                "error_message": row.error_message,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    async def _get_one(self, query: Select, id: UUID):
        result = await self.connection.execute(query)
        if not (row := result.fetchone()):
            raise EntityNotFoundError(entity="task", id=str(id))
        return self._to_task(row) 