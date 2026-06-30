from abc import ABC
from typing import Generic

from basalam.backbone_orm import PostgresConnection, RepositoryAbstract as BaseRepositoryAbstract, T, V

from setup.dbs.postgres import main_postgres


class AgnoRepositoryAbstract(BaseRepositoryAbstract, ABC, Generic[T, V]):
    @classmethod
    async def connection(cls) -> PostgresConnection:
        return await main_postgres()
