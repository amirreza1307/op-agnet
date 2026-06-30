"""Base SDK for external service integrations.

Provides common HTTP client setup, authentication abstractions,
decorators, and exception hierarchy for all vendor-agent SDKs.
"""

from __future__ import annotations

import abc
import asyncio
import random
from functools import wraps
from typing import Any, Callable, Optional

import httpx

DEFAULT_MAX_RETRIES = 1
DEFAULT_RETRY_DELAY = 1.0
DEFAULT_RETRY_JITTER = 0.1

DEFAULT_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SDKException(Exception):
    def __init__(self, message: str, error_type: Optional[str] = None):
        super().__init__(message)
        self.error_type = error_type


class SDKTimeoutException(SDKException):
    pass


class SDKConnectionException(SDKException):
    pass


class SDKResponseException(SDKException):
    def __init__(
        self,
        message: str,
        response: httpx.Response,
        error_type: Optional[str] = None,
    ):
        super().__init__(message, error_type)
        self.response = response
        self.status_code = response.status_code


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------


def timeout_guard(func: Callable) -> Callable:
    """Convert httpx timeout / connect errors to SDK exceptions."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except httpx.ReadTimeout:
            raise SDKTimeoutException(
                f"Read timeout in {self.__class__.__name__}",
                error_type="read_timeout",
            )
        except httpx.TimeoutException:
            raise SDKTimeoutException(
                f"Timeout in {self.__class__.__name__}",
                error_type="timeout",
            )
        except httpx.ConnectError:
            raise SDKConnectionException(
                f"Connection error in {self.__class__.__name__}",
                error_type="connect_error",
            )

    return wrapper


def with_auth_token(func: Callable) -> Callable:
    """Automatically call ``_set_auth_token`` before the wrapped method."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        await self._set_auth_token()
        return await func(self, *args, **kwargs)

    return wrapper


def with_secret_key(func: Callable) -> Callable:
    """Automatically call ``_set_secret_key`` before the wrapped method."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        await self._set_secret_key()
        return await func(self, *args, **kwargs)

    return wrapper


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    delay: float = DEFAULT_RETRY_DELAY,
    jitter: float = DEFAULT_RETRY_JITTER,
    retry_status_codes: Optional[set[int]] = None,
):
    """Retry on transient SDK errors with exponential back-off."""
    status_codes = retry_status_codes or DEFAULT_RETRY_STATUS_CODES

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            last_exception: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(self, *args, **kwargs)
                except (SDKTimeoutException, SDKConnectionException) as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        wait = delay * (2**attempt) + random.uniform(0, jitter)
                        await asyncio.sleep(wait)
                        continue
                    raise
                except SDKResponseException as exc:
                    if exc.status_code in status_codes and attempt < max_retries:
                        wait = delay * (2**attempt) + random.uniform(0, jitter)
                        await asyncio.sleep(wait)
                        continue
                    raise
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseSDK(abc.ABC):
    """Abstract base for all external-service SDKs."""

    def __init__(
        self,
        base_url: str,
        user_agent: str = "VendorAgent/1.0",
        timeout: float = 30.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        if http_client:
            self._http_client = http_client
        else:
            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
            )
        self._http_client.base_url = base_url.rstrip("/")
        self._http_client.headers["User-Agent"] = user_agent

    @abc.abstractmethod
    async def _set_auth_token(self) -> None: ...

    @abc.abstractmethod
    async def _set_secret_key(self) -> None: ...

    async def close(self) -> None:
        await self._http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
