from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from setup.config import config


def _is_documented_path(path: str) -> bool:
    """Single source of truth for which paths appear in the OpenAPI schema.

    Only the public ``/v1`` API is documented. Every other route group
    (``/platform``, ``/healthz``, ``/readyz``, ...) stays fully callable but
    hidden from the docs. Change the rule here to adjust what the docs expose.
    """
    return path.startswith("/v1/") and not path.startswith("/v1/preview")


def customize_openapi(app: FastAPI) -> None:
    def openapi():
        schema = get_openapi(
            title="Agent Graph Platform",
            version="1.0.0",
            routes=app.routes,
        )
        # Filter the generated schema down to the documented (v1) paths only.
        # Routes themselves are untouched, so every endpoint remains callable;
        # we only hide non-v1 paths from the generated schema / Swagger UI.
        paths = schema.get("paths")
        if isinstance(paths, dict):
            for path in [p for p in paths if not _is_documented_path(p)]:
                del paths[path]
        schema.setdefault("components", {}).setdefault("securitySchemes", {}).update({
            "AdminSecretKey": {
                "type": "apiKey",
                "in": "header",
                "name": config.ADMIN_SECRET_HEADER_NAME or "X-Admin-Secret-Key",
            },
            "BearerToken": {
                "type": "http",
                "scheme": "bearer",
            },
            "AgentApiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Agent-API-Key",
            },
        })
        return schema

    app.openapi = openapi

    @app.get("/swagger.json", include_in_schema=False)
    def swagger_json():
        return JSONResponse(app.openapi())
