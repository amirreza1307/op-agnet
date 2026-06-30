from abc import ABC
from typing import Generic
from basalam.backbone_orm import RepositoryAbstract as BaseRepositoryAbstract, PostgresConnection, T, V
from setup.dbs.postgres import main_postgres


class MainRepositoryAbstract(BaseRepositoryAbstract, ABC, Generic[T, V]):

    @classmethod
    async def connection(cls) -> PostgresConnection:
        return await main_postgres()