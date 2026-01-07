"""
Custom exception classes for the application.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class ParacleteException(HTTPException):
    """Base exception for Paraclete application."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class AuthenticationError(ParacleteException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(ParacleteException):
    """Raised when user lacks permission for an action."""

    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class NotFoundError(ParacleteException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{identifier}' not found",
        )


class ValidationError(ParacleteException):
    """Raised when input validation fails."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class ConflictError(ParacleteException):
    """Raised when there's a conflict with existing data."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class RateLimitError(ParacleteException):
    """Raised when rate limit is exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )


class ExternalServiceError(ParacleteException):
    """Raised when an external service fails."""

    def __init__(self, service: str, detail: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External service '{service}' error: {detail}",
        )


class SessionError(ParacleteException):
    """Raised when session operations fail."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session error: {detail}",
        )


class WebSocketError(Exception):
    """Base exception for WebSocket errors."""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(reason)