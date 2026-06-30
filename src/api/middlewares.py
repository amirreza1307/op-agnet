from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from setup.dbs.postgres import release_all_postgres_connections
from setup.request_context import RequestContext


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        released = False

        async def send_wrapper(message: dict) -> None:
            nonlocal released
            await send(message)
            if (
                not released
                and message["type"] == "http.response.body"
                and not message.get("more_body", False)
            ):
                released = True
                try:
                    await release_all_postgres_connections()
                except Exception:
                    pass

        with RequestContext(request):
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                if not released:
                    try:
                        await release_all_postgres_connections()
                    except Exception:
                        pass

