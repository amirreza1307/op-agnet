import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.errors import ApiError
from api.exception_handlers import (
    api_exception_handler,
    general_exception_handler,
    timeout_exception_handler,
    validation_exception_handler,
)
from api.middlewares import RequestContextMiddleware
from api.response_models.common.common_response_models import (
    HealthResponseModel,
    ReadinessResponseModel,
)
from api.routes import router as api_router
from setup.app_bootstrap.asyncio_filter import install_asyncio_exception_filter, restore_asyncio_exception_filter
from setup.app_bootstrap.openapi import customize_openapi
from setup.app_bootstrap.proxy import close_proxy_client, register_proxy_routes
from setup.app_bootstrap.spa import register_spa
from setup.bootstrap import bootstrap_application_state
from setup.config import config
from setup.dbs.postgres import (
    main_postgres,
    main_release_postgres,
    release_all_postgres_connections,
)

logger = logging.getLogger(__name__)

if not config.DEBUG and config.SENTRY_DSN:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN, debug=config.SENTRY_DEBUG_ENABLED,
        release=config.SENTRY_RELEASE or None,
        environment=config.SENTRY_ENVIRONMENT or config.APP_ENV,
        traces_sample_rate=config.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=config.SENTRY_PROFILES_SAMPLE_RATE,
        auto_session_tracking=config.SENTRY_AUTO_SESSION_TRACKING,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        install_asyncio_exception_filter()
        await bootstrap_application_state()
        await release_all_postgres_connections()
        yield
    finally:
        restore_asyncio_exception_filter()
        await close_proxy_client()
        await release_all_postgres_connections()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)
app.add_middleware(
    # Fail closed: an empty `admin_allowed_origins` should reject all
    # cross-origin requests, not fall back to `["*"]` (which Starlette would
    # silently strip anyway because `allow_credentials=True` forbids `*`).
    # Configure ADMIN_ALLOWED_ORIGINS in env to enable CORS for a deployment.
    CORSMiddleware, allow_origins=config.admin_allowed_origins,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ApiError, api_exception_handler)
app.add_exception_handler(TimeoutError, timeout_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/healthz", response_model=HealthResponseModel)
async def healthz():
    """Liveness probe: the process is up and the event loop is responsive.

    Intentionally does not touch external dependencies. Dependency health is
    reported by ``/readyz``.
    """
    return {"status": "ok"}


async def _check_postgres() -> str:
    try:
        connection = await main_postgres()
        try:
            await connection.execute_and_fetch("SELECT 1;")
        finally:
            await main_release_postgres()
        return "ok"
    except Exception as exc:
        logger.warning("Readiness probe: Postgres check failed: %s", exc)
        return f"error: {type(exc).__name__}"


@app.get("/readyz", response_model=ReadinessResponseModel)
async def readyz():
    """Readiness probe: every critical dependency is reachable.

    Kubernetes routes traffic to a pod only while this returns 200. If Postgres
    is down, returning 503 drains traffic until the pod recovers.
    """
    checks = {
        "postgres": await _check_postgres(),
    }
    healthy = all(value == "ok" for value in checks.values())
    payload = {"status": "ready" if healthy else "degraded", "checks": checks}
    if not healthy:
        return JSONResponse(status_code=503, content=payload)
    return payload


register_proxy_routes(app)
register_spa(app)

# Always filter the OpenAPI schema down to the public /v1 API, in every
# environment — so /docs, /openapi.json and /swagger.json only ever expose v1,
# never internal platform routes.
customize_openapi(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
