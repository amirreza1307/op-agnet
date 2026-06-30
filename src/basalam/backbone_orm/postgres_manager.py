from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import asyncpg


class DriverEnum(Enum):
    POOL = "pool"
    SINGLE = "single"
    TEST = "test"


@dataclass
class ConnectionConfig:
    pool_min_size: int = 1
    pool_max_size: int = 10
    pool_acquire_timeout: float = 30.0
    user: str = "postgres"
    password: str = ""
    host: str = "localhost"
    port: int = 5432
    db: str = "postgres"
    pool_max_inactive_connection_lifetime: float = 300.0
    timeout: float = 30.0


class PostgresConnection:
    def __init__(self, connection: asyncpg.Connection):
        self.__connection = connection

    async def fetch(self, query: str, *args: Any):
        return await self.__connection.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any):
        return await self.__connection.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any):
        return await self.__connection.execute(query, *args)

    async def execute_and_fetch(self, query: str, args: Optional[list[Any]] = None):
        rows = await self.__connection.fetch(query, *(args or []))
        return [dict(row) for row in rows]

    def transaction(self, *args: Any, **kwargs: Any):
        return self.__connection.transaction(*args, **kwargs)


class _PoolDriver:
    def __init__(self, config: ConnectionConfig):
        self._config = config
        self.__pool: Optional[asyncpg.Pool] = None
        self.__acquires: dict[Any, tuple[PostgresConnection, asyncpg.Connection]] = {}

    async def _pool(self) -> asyncpg.Pool:
        if self.__pool is None:
            self.__pool = await asyncpg.create_pool(
                user=self._config.user,
                password=self._config.password,
                host=self._config.host,
                port=self._config.port,
                database=self._config.db,
                min_size=self._config.pool_min_size,
                max_size=self._config.pool_max_size,
                max_inactive_connection_lifetime=self._config.pool_max_inactive_connection_lifetime,
                timeout=self._config.timeout,
            )
        return self.__pool

    async def acquire(self, key: Any = None) -> PostgresConnection:
        if key is not None and key in self.__acquires:
            return self.__acquires[key][0]
        raw = await (await self._pool()).acquire(timeout=self._config.pool_acquire_timeout)
        wrapped = PostgresConnection(raw)
        if key is not None:
            self.__acquires[key] = (wrapped, raw)
        return wrapped

    async def release(self, key: Any = None) -> None:
        if key is None:
            return
        entry = self.__acquires.pop(key, None)
        if entry is None:
            return
        await (await self._pool()).release(entry[1])


class _SingleDriver:
    def __init__(self, config: ConnectionConfig):
        self._config = config
        self.__connection: Optional[tuple[PostgresConnection, asyncpg.Connection]] = None

    async def acquire(self, key: Any = None) -> PostgresConnection:
        raw = None if self.__connection is None else self.__connection[1]
        if raw is None or raw.is_closed():
            raw = await asyncpg.connect(
                user=self._config.user,
                password=self._config.password,
                host=self._config.host,
                port=self._config.port,
                database=self._config.db,
                timeout=self._config.timeout,
            )
            self.__connection = (PostgresConnection(raw), raw)
        return self.__connection[0]

    async def release(self, key: Any = None) -> None:
        return None


class PostgresManager:
    def __init__(self, config: ConnectionConfig):
        self.__drivers = {
            DriverEnum.POOL: _PoolDriver(config),
            DriverEnum.SINGLE: _SingleDriver(config),
            DriverEnum.TEST: _SingleDriver(config),
        }

    async def acquire(self, driver: DriverEnum = DriverEnum.POOL, key: Any = None) -> PostgresConnection:
        return await self.__drivers[driver].acquire(key)

    async def release(self, driver: DriverEnum = DriverEnum.POOL, key: Any = None) -> None:
        return await self.__drivers[driver].release(key)
