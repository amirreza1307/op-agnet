from contextvars import ContextVar
from typing import Optional, Any

from starlette.requests import Request


class RequestContext:
    __context: ContextVar = ContextVar("request", default=None)

    def __init__(self, request: Request) -> None:
        self.__request = request
        self.__context_instance = None

    def __enter__(self):
        if self.__context_instance is None:
            self.__context_instance = self.__context.set(self.__request)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__context.reset(self.__context_instance)

    @classmethod
    def get(cls) -> Optional["Request"]:
        return cls.__context.get()

    @classmethod
    def clear(cls) -> None:
        cls.__context.set(None)

    @classmethod
    def set_property(cls, key: Any, value: Any):
        cls.get().state.__setattr__(key, value)

    @classmethod
    def get_property(cls, key: Any, default: Any = None):
        try:
            return cls.get().state.__getattr__(key)
        except AttributeError:
            return default
