"""Unrealon SDK exception classes."""

from __future__ import annotations


class UnrealonError(Exception):
    """Base exception for all Unrealon SDK errors."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        suggestion: str | None = None,
        original_error: Exception | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.suggestion = suggestion
        self.original_error = original_error

        # Build full message
        full_message = message
        if suggestion:
            full_message = f"{message}\n\nSuggestion: {suggestion}"

        super().__init__(full_message)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r})"
        )


class APIError(UnrealonError):
    """Error from API response."""

    pass


class AuthenticationError(UnrealonError):
    """Invalid or missing API key."""

    pass


class RegistrationError(UnrealonError):
    """Parser registration failed."""

    pass


class HeartbeatError(UnrealonError):
    """Heartbeat failed."""

    pass


class ValidationError(UnrealonError):
    """Invalid request parameters."""

    pass


class TimeoutError(UnrealonError):
    """Request timed out."""

    pass


class NetworkError(UnrealonError):
    """Network connection error."""

    pass


class NotFoundError(UnrealonError):
    """Resource not found (404)."""

    pass


class RateLimitError(UnrealonError):
    """Rate limit exceeded."""

    pass
