from __future__ import annotations

from typing import Any, Optional


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = 400,
        error_code: str = "api_error",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details


class BadRequestError(ApiError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, status_code=400, error_code="bad_request", details=details)


class UnauthorizedError(ApiError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, status_code=401, error_code="unauthorized", details=details)


class ForbiddenError(ApiError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, status_code=403, error_code="forbidden", details=details)


class NotFoundError(ApiError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, status_code=404, error_code="not_found", details=details)


class ConflictError(ApiError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, status_code=409, error_code="conflict", details=details)


class ServiceUnavailableError(ApiError):
    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, status_code=503, error_code="service_unavailable", details=details)

