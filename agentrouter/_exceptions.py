"""Custom exceptions for the agentrouter SDK."""

from __future__ import annotations


class AgentRouterError(Exception):
    """Base class for all agentrouter SDK errors."""


class AuthenticationError(AgentRouterError):
    """Raised when the API key is missing, invalid, or rejected (HTTP 401/403)."""
    def __init__(self, message: str = "Invalid or missing API key.", status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class APIError(AgentRouterError):
    """Raised when the API returns a non-2xx response."""
    def __init__(self, message: str, status_code: int, body: object = None) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class APITimeoutError(AgentRouterError):
    """Raised when a request times out."""


class APIConnectionError(AgentRouterError):
    """Raised when a network-level error occurs."""


class BadRequestError(APIError):
    """HTTP 400."""


class PermissionDeniedError(APIError):
    """HTTP 403."""


class NotFoundError(APIError):
    """HTTP 404."""


class RateLimitError(APIError):
    """HTTP 429."""


class InternalServerError(APIError):
    """HTTP 5xx."""
