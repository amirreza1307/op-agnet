from typing import Any, Dict, Optional

from starlette.requests import Request

from setup.request_context import RequestContext


class ControllerAbstract:

    @property
    def request(self) -> Optional[Request]:
        return RequestContext.get()

    @classmethod
    def okay(cls, message: str = "OK") -> Dict[str, str]:
        return {"message": message}

    def json(self, **kwargs: Any) -> Dict[str, Any]:
        return {**kwargs}

