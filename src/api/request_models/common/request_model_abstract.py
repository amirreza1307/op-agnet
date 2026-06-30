from typing import Any, Callable, Dict
from pydantic import BaseModel, PrivateAttr


class RequestModelAbstract(BaseModel):
    __cached: Dict[str, Any] = PrivateAttr({})

    async def cached(self, name: str, callback: Callable) -> Any:
        if name not in self.__cached:
            self.__cached[name] = await (callback())
        return self.__cached[name]

