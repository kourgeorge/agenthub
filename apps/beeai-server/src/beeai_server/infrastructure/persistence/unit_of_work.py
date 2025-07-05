# Copyright 2025 © BeeAI a Series of LF Projects, LLC
# SPDX-License-Identifier: Apache-2.0

from contextlib import suppress
from typing import Self

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection, AsyncTransaction

from beeai_server.configuration import Configuration
from beeai_server.domain.repositories.agent import IAgentRepository
from beeai_server.domain.repositories.env import IEnvVariableRepository
from beeai_server.domain.repositories.file import IFileRepository
from beeai_server.domain.repositories.provider import IProviderRepository
from beeai_server.domain.repositories.user import IUserRepository
from beeai_server.domain.repositories.vector_store import IVectorStoreRepository, IVectorDatabaseRepository
from beeai_server.domain.repositories.task import ITaskRepository
from beeai_server.domain.repositories.credits import ICreditsRepository
from beeai_server.infrastructure.persistence.repositories.file import SqlAlchemyFileRepository
from beeai_server.infrastructure.persistence.repositories.agent import SqlAlchemyAgentRepository
from beeai_server.infrastructure.persistence.repositories.env import SqlAlchemyEnvVariableRepository
from beeai_server.infrastructure.persistence.repositories.provider import SqlAlchemyProviderRepository
from beeai_server.infrastructure.persistence.repositories.user import SqlAlchemyUserRepository
from beeai_server.infrastructure.persistence.repositories.vector_store import SqlAlchemyVectorStoreRepository
from beeai_server.infrastructure.persistence.repositories.task import SqlAlchemyTaskRepository
from beeai_server.infrastructure.persistence.repositories.credits import SqlAlchemyCreditsRepository
from beeai_server.infrastructure.vector_database.vector_db import VectorDatabaseRepository
from beeai_server.service_layer.unit_of_work import IUnitOfWork, IUnitOfWorkFactory


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """
    One UoW == one DB transaction.
    Works purely with SQLAlchemy Core objects (insert(), update(), text(), …).
    """

    providers: IProviderRepository
    agents: IAgentRepository
    env: IEnvVariableRepository
    files: IFileRepository
    users: IUserRepository
    vector_stores: IVectorStoreRepository
    vector_database: IVectorDatabaseRepository
    tasks: ITaskRepository
    credits: ICreditsRepository

    def __init__(self, engine: AsyncEngine, config: Configuration) -> None:
        self._engine: AsyncEngine = engine
        self._connection: AsyncConnection | None = None
        self._transaction: AsyncTransaction | None = None
        self._config = config

    async def __aenter__(self) -> Self:
        if self._connection or self._transaction:
            raise RuntimeError("Unit of Work is already active. It cannot be re-entered.")
        try:
            self._connection = await self._engine.connect()
            self._transaction = await self._connection.begin()

            self.providers = SqlAlchemyProviderRepository(self._connection)
            self.agents = SqlAlchemyAgentRepository(self._connection)
            self.env = SqlAlchemyEnvVariableRepository(self._connection, configuration=self._config)
            self.files = SqlAlchemyFileRepository(self._connection)
            self.users = SqlAlchemyUserRepository(self._connection)
            self.vector_stores = SqlAlchemyVectorStoreRepository(self._connection)
            self.vector_database = VectorDatabaseRepository(
                self._connection, schema_name=self._config.persistence.vector_db_schema
            )
            self.tasks = SqlAlchemyTaskRepository(self._connection)
            self.credits = SqlAlchemyCreditsRepository(self._connection)

        except Exception as e:
            if self._connection:
                await self._connection.close()
            self._connection = None
            self._transaction = None
            raise RuntimeError(f"Failed to enter Unit of Work: {e}") from e

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._transaction:
            with suppress(Exception):
                if exc_type is None:
                    await self._transaction.commit()
                else:
                    await self._transaction.rollback()
            self._transaction = None

        if self._connection:
            await self._connection.close()
            self._connection = None

    async def commit(self) -> None:
        if self._transaction:
            await self._transaction.commit()
            self._transaction = await self._connection.begin()

    async def rollback(self) -> None:
        if self._transaction:
            await self._transaction.rollback()
            self._transaction = await self._connection.begin()


class SqlAlchemyUnitOfWorkFactory(IUnitOfWorkFactory):
    def __init__(self, engine: AsyncEngine, config: Configuration) -> None:
        self.engine = engine
        self._config = config

    def __call__(self) -> SQLAlchemyUnitOfWork:
        return SQLAlchemyUnitOfWork(self.engine, config=self._config)
