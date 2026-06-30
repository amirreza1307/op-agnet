from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse


_FRONTEND_DIST = Path("/app/frontend/dist")


def register_spa(app: FastAPI) -> None:
    if not _FRONTEND_DIST.exists():
        return

    app.mount("/static", StaticFiles(directory=_FRONTEND_DIST), name="frontend-static")

    index_html = (_FRONTEND_DIST / "index.html").read_text(encoding="utf-8")

    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        path = request.url.path
        if path.startswith(("/platform", "/vendor", "/healthz", "/.well-known", "/uploadio", "/docs", "/openapi.json", "/swagger.json")):
            return await call_next(request)

        static_file = _FRONTEND_DIST / path.lstrip("/")
        if static_file.is_file():
            return FileResponse(static_file)

        response = await call_next(request)
        if response.status_code == 404:
            return HTMLResponse(index_html)
        return response
