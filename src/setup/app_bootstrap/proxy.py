import httpx
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response


_proxy_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)


def _make_proxy(target_base_url: str, host_header: str, strip_prefix: str):
    async def _proxy_handler(request: Request):
        path = request.url.path
        if strip_prefix:
            path = path[len(strip_prefix):] or "/"
        target_url = f"{target_base_url.rstrip('/')}{path}"
        if request.url.query:
            target_url += f"?{request.url.query}"

        headers = {}
        for k, v in request.headers.items():
            if k.lower() not in ("host", "transfer-encoding", "accept-encoding"):
                headers[k] = v
        headers["Host"] = host_header
        headers["Accept-Encoding"] = "identity"

        body = await request.body()
        resp = await _proxy_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body or None,
        )
        excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        resp_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded}
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=resp_headers,
        )
    return _proxy_handler


def register_proxy_routes(app: FastAPI) -> None:
    app.api_route(
        "/uploadio/{path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        include_in_schema=False,
    )(_make_proxy("https://uploadio.basalam.com", "uploadio.basalam.com", "/uploadio"))


async def close_proxy_client() -> None:
    await _proxy_client.aclose()
