# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from uuid import UUID
from decimal import Decimal

from sqlalchemy import Table, Column, String, ForeignKey, UUID as SqlUUID, DateTime, Numeric, Select, Row
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import select, insert, update

from beeai_server.domain.models.agent import Credits
from beeai_server.domain.repositories.credits import ICreditsRepository
from beeai_server.exceptions import EntityNotFoundError, DuplicateEntityError
from beeai_server.infrastructure.persistence.repositories.db_metadata import metadata
from beeai_server.utils.utils import utc_now

credits_table = Table(
    "credits",
    metadata,
    Column("user_id", SqlUUID, primary_key=True),
    Column("balance", Numeric(10, 2), nullable=False, default=0),
    Column("currency", String(3), nullable=False, default="USD"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class SqlAlchemyCreditsRepository(ICreditsRepository):
    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def create(self, credits: Credits) -> None:
        query = insert(credits_table).values(
            user_id=credits.user_id,
            balance=credits.balance,
            currency=credits.currency,
            created_at=credits.created_at,
            updated_at=credits.updated_at,
        )
        try:
            await self.connection.execute(query)
        except IntegrityError:
            raise DuplicateEntityError(entity="credits", field="user_id", value=str(credits.user_id))

    async def get(self, *, user_id: UUID) -> Credits:
        return await self._get_one(credits_table.select().where(credits_table.c.user_id == user_id), user_id=user_id)

    async def update(self, *, credits: Credits) -> None:
        query = (
            credits_table.update()
            .where(credits_table.c.user_id == credits.user_id)
            .values(
                balance=credits.balance,
                currency=credits.currency,
                updated_at=credits.updated_at,
            )
        )
        await self.connection.execute(query)

    async def add_credits(self, *, user_id: UUID, amount: Decimal) -> bool:
        query = (
            credits_table.update()
            .where(credits_table.c.user_id == user_id)
            .values(
                balance=credits_table.c.balance + amount,
                updated_at=utc_now(),
            )
        )
        result = await self.connection.execute(query)
        return result.rowcount > 0

    async def deduct_credits(self, *, user_id: UUID, amount: Decimal) -> bool:
        # First check if user has sufficient balance
        current_credits = await self.get(user_id=user_id)
        if current_credits.balance < amount:
            return False
        
        query = (
            credits_table.update()
            .where(credits_table.c.user_id == user_id)
            .values(
                balance=credits_table.c.balance - amount,
                updated_at=utc_now(),
            )
        )
        result = await self.connection.execute(query)
        return result.rowcount > 0

    async def get_balance(self, *, user_id: UUID) -> Decimal:
        credits = await self.get(user_id=user_id)
        return credits.balance

    def _to_credits(self, row: Row) -> Credits:
        return Credits.model_validate(
            {
                "user_id": row.user_id,
                "balance": row.balance,
                "currency": row.currency,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    async def _get_one(self, query: Select, user_id: UUID):
        result = await self.connection.execute(query)
        if not (row := result.fetchone()):
            raise EntityNotFoundError(entity="credits", id=str(user_id))
        return self._to_credits(row) 