from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Generic, Optional, Type, TypeVar

from pydantic import BaseModel, ConfigDict

from .postgres_manager import ConnectionConfig, DriverEnum, PostgresConnection, PostgresManager

T = TypeVar("T", bound="ModelAbstract")
V = TypeVar("V")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ModelAbstract(BaseModel):
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class ModelSchemaAbstract:
    pass


@dataclass(frozen=True)
class Condition:
    column: str
    operator: str
    value: Any


class Field:
    def __init__(self, column: str):
        self.column = column

    def eq(self, value: Any) -> Condition:
        return Condition(self.column, "=", value)


@dataclass
class QueryBuilderAbstract:
    repo: Type["RepositoryAbstract"]
    selected: list[str] = field(default_factory=lambda: ["*"])
    conditions: list[Condition] = field(default_factory=list)
    orderings: list[tuple[str, str]] = field(default_factory=list)
    limit_count: Optional[int] = None
    offset_count: Optional[int] = None

    def select(self, *columns: str) -> "QueryBuilderAbstract":
        self.selected = list(columns or ["*"])
        return self

    def where(self, condition: Condition) -> "QueryBuilderAbstract":
        self.conditions.append(condition)
        return self

    def orderby(self, column: str, order: Any = None) -> "QueryBuilderAbstract":
        direction = _order_to_sql(order)
        self.orderings.append((column, direction))
        return self

    def limit(self, count: int) -> "QueryBuilderAbstract":
        self.limit_count = count
        return self

    def offset(self, count: int) -> "QueryBuilderAbstract":
        self.offset_count = count
        return self


class RepositoryAbstract(Generic[T, V]):
    @classmethod
    def schema_name(cls) -> str:
        raise NotImplementedError

    @classmethod
    def table_name(cls) -> str:
        raise NotImplementedError

    @classmethod
    def model(cls) -> Type[T]:
        raise NotImplementedError

    @classmethod
    async def connection(cls) -> PostgresConnection:
        raise NotImplementedError

    @classmethod
    def select_query(cls) -> QueryBuilderAbstract:
        return QueryBuilderAbstract(repo=cls)

    @classmethod
    def field(cls, column: str) -> Field:
        return Field(column)

    @classmethod
    async def get(cls, query: QueryBuilderAbstract) -> list[T]:
        sql, args = cls._select_sql(query)
        rows = await (await cls.connection()).fetch(sql, *args)
        return [cls.model().model_validate(dict(row)) for row in rows]

    @classmethod
    async def first(cls, query: QueryBuilderAbstract) -> Optional[T]:
        query.limit(1)
        rows = await cls.get(query)
        return rows[0] if rows else None

    @classmethod
    async def count(cls, query: QueryBuilderAbstract) -> int:
        where_sql, args = cls._where_sql(query.conditions)
        row = await (await cls.connection()).fetchrow(
            f"SELECT COUNT(*) AS total FROM {cls._table_sql()}{where_sql}",
            *args,
        )
        return int(row["total"]) if row else 0

    @classmethod
    async def create_return(cls, payload: dict[str, Any]) -> T:
        data = cls._prepare_payload(payload)
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ", ".join(f"${index}" for index in range(1, len(values) + 1))
        sql = (
            f"INSERT INTO {cls._table_sql()} ({', '.join(_quote_identifier(c) for c in columns)}) "
            f"VALUES ({placeholders}) RETURNING *"
        )
        row = await (await cls.connection()).fetchrow(sql, *values)
        return cls.model().model_validate(dict(row))

    @classmethod
    async def update_by_id(
        cls,
        record_id: Any,
        payload: dict[str, Any],
        return_: bool = False,
    ) -> Optional[T]:
        data = cls._prepare_payload(payload)
        if not data:
            return await cls._find_by_id(record_id) if return_ else None
        assignments = [
            f"{_quote_identifier(column)} = ${index}"
            for index, column in enumerate(data.keys(), start=1)
        ]
        values = list(data.values())
        id_param = len(values) + 1
        returning = " RETURNING *" if return_ else ""
        sql = (
            f"UPDATE {cls._table_sql()} SET {', '.join(assignments)} "
            f"WHERE {_quote_identifier('id')} = ${id_param}{returning}"
        )
        connection = await cls.connection()
        if return_:
            row = await connection.fetchrow(sql, *values, record_id)
            return cls.model().model_validate(dict(row)) if row else None
        await connection.execute(sql, *values, record_id)
        return None

    @classmethod
    async def _find_by_id(cls, record_id: Any) -> Optional[T]:
        query = cls.select_query().where(cls.field("id").eq(record_id)).select("*")
        return await cls.first(query)

    @classmethod
    def _select_sql(cls, query: QueryBuilderAbstract) -> tuple[str, list[Any]]:
        columns = ", ".join("*" if column == "*" else _quote_identifier(column) for column in query.selected)
        where_sql, args = cls._where_sql(query.conditions)
        order_sql = ""
        if query.orderings:
            order_sql = " ORDER BY " + ", ".join(
                f"{_quote_identifier(column)} {direction}" for column, direction in query.orderings
            )
        limit_sql = f" LIMIT {int(query.limit_count)}" if query.limit_count is not None else ""
        offset_sql = f" OFFSET {int(query.offset_count)}" if query.offset_count is not None else ""
        return f"SELECT {columns} FROM {cls._table_sql()}{where_sql}{order_sql}{limit_sql}{offset_sql}", args

    @classmethod
    def _where_sql(cls, conditions: list[Condition]) -> tuple[str, list[Any]]:
        if not conditions:
            return "", []
        args: list[Any] = []
        parts: list[str] = []
        for condition in conditions:
            args.append(_serialize_value(condition.value))
            parts.append(f"{_quote_identifier(condition.column)} {condition.operator} ${len(args)}")
        return " WHERE " + " AND ".join(parts), args

    @classmethod
    def _table_sql(cls) -> str:
        return f"{_quote_identifier(cls.schema_name())}.{_quote_identifier(cls.table_name())}"

    @classmethod
    def _prepare_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        return {key: _serialize_value(value) for key, value in payload.items() if value is not None}


def _quote_identifier(identifier: str) -> str:
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return f'"{identifier}"'


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, (datetime, date)):
        return value
    return value


def _order_to_sql(order: Any) -> str:
    if order is None:
        return "ASC"
    value = getattr(order, "value", order)
    text = str(value).lower()
    return "DESC" if "desc" in text else "ASC"


__all__ = [
    "ConnectionConfig",
    "DriverEnum",
    "Field",
    "ModelAbstract",
    "ModelSchemaAbstract",
    "PostgresConnection",
    "PostgresManager",
    "QueryBuilderAbstract",
    "RepositoryAbstract",
    "T",
    "V",
]
