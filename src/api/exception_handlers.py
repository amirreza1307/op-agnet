import json
import logging

import sentry_sdk
from api.errors import ApiError
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.requests import Request

from setup.config import config

logger = logging.getLogger(__name__)


def _serialize_errors(errors: list) -> list:
    text = json.dumps(errors, default=str, ensure_ascii=False)
    return json.loads(text)


async def validation_exception_handler(request: Request, exception: RequestValidationError):
    return ORJSONResponse(
        {
            "type": "validation_error",
            "message": "The given data was invalid.",
            "errors": _serialize_errors(exception.errors()),
        },
        status_code=422,
    )


async def api_exception_handler(request: Request, exception: ApiError):
    payload = {"type": exception.error_code, "message": str(exception)}
    if exception.details:
        payload["details"] = exception.details
    if exception.status_code >= 500:
        logger.exception(
            "api_error: %s (%s)",
            exception.error_code,
            exception.status_code,
            exc_info=exception,
        )
        if config.SENTRY_DSN:
            sentry_sdk.capture_exception(exception)
    return ORJSONResponse(payload, status_code=exception.status_code)


_DEBUG_ENVIRONMENTS = {"local", "development", "dev", "staging", "stage", "test"}


def _is_debug_environment() -> bool:
    env = (config.APP_ENV or "").strip().lower()
    return config.DEBUG or env in _DEBUG_ENVIRONMENTS


async def timeout_exception_handler(request: Request, exception: TimeoutError):
    logger.warning("Request timed out waiting on a backend resource: %s", exception)
    if config.SENTRY_DSN:
        sentry_sdk.capture_exception(exception)
    return ORJSONResponse(
        {"type": "service_unavailable", "message": "Service is temporarily unavailable. Please retry."},
        status_code=503,
    )


async def general_exception_handler(request: Request, exception: Exception):
    logger.exception("Unhandled exception")

    if config.SENTRY_DSN:
        sentry_sdk.capture_exception(exception)

    if not _is_debug_environment():
        return ORJSONResponse(
            {"type": "internal_error", "message": "Internal Server Error"},
            status_code=500,
        )

    import traceback

    try:
        msg = str(exception)
    except Exception:
        msg = repr(exception)
    return ORJSONResponse(
        {
            "type": exception.__class__.__name__,
            "message": msg,
            "traceback": traceback.format_exception(type(exception), exception, exception.__traceback__),
        },
        status_code=500,
    )

