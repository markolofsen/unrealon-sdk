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


class InterruptError(BaseException):
    """Service interrupted by pause/stop command.

    Inherits from BaseException (not Exception) so that generic
    `except Exception` blocks don't catch it - only explicit
    `except InterruptError` or `except BaseException` will catch it.

    Raised by check_interrupt() when pause or stop is requested.
    Parsers should catch this to cleanly exit processing loops.
    """

    def __init__(self, reason: str = "interrupted"):
        super().__init__(f"Service {reason}")
        self.reason = reason
        self.message = f"Service {reason}"


class PauseInterrupt(InterruptError):
    """Service paused by command."""

    def __init__(self):
        super().__init__(reason="paused")


class StopInterrupt(InterruptError):
    """Service stopped by command."""

    def __init__(self):
        super().__init__(reason="stopped")
