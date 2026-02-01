"""Error handling decorators and helpers."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any, ParamSpec, TypeVar

import httpx

from .types import (
    APIError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    UnrealonError,
    ValidationError,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def parse_api_error(
    status_code: int,
    error_body: Any,
    original_error: Exception,
) -> UnrealonError:
    """Parse API error response and return appropriate exception."""

    # Extract message from error body
    if isinstance(error_body, dict):
        message = error_body.get("detail") or error_body.get("message") or str(error_body)
        error_code = error_body.get("code")
    else:
        message = str(error_body)
        error_code = None

    # Map status codes to exception types
    if status_code == 401:
        return AuthenticationError(
            message=message or "Invalid or missing API key",
            status_code=status_code,
            error_code=error_code,
            suggestion="Check your UNREALON_API_KEY environment variable",
            original_error=original_error,
        )
    elif status_code == 403:
        return AuthenticationError(
            message=message or "Access forbidden",
            status_code=status_code,
            error_code=error_code,
            suggestion="Check API key permissions",
            original_error=original_error,
        )
    elif status_code == 404:
        return NotFoundError(
            message=message or "Resource not found",
            status_code=status_code,
            error_code=error_code,
            suggestion="Check the parser ID or API endpoint",
            original_error=original_error,
        )
    elif status_code == 422:
        return ValidationError(
            message=message or "Validation error",
            status_code=status_code,
            error_code=error_code,
            original_error=original_error,
        )
    elif status_code == 429:
        return RateLimitError(
            message=message or "Rate limit exceeded",
            status_code=status_code,
            error_code=error_code,
            suggestion="Reduce request frequency",
            original_error=original_error,
        )
    else:
        return APIError(
            message=message or f"API error (status {status_code})",
            status_code=status_code,
            error_code=error_code,
            original_error=original_error,
        )


@contextmanager
def handle_api_errors():
    """Context manager to catch and convert httpx errors to SDK exceptions."""
    try:
        yield
    except httpx.HTTPStatusError as e:
        try:
            error_body = e.response.json()
        except Exception:
            error_body = e.response.text

        logger.debug("API error: status=%d, body=%s", e.response.status_code, error_body)
        raise parse_api_error(
            status_code=e.response.status_code,
            error_body=error_body,
            original_error=e,
        ) from e
    except httpx.TimeoutException as e:
        logger.debug("Timeout error: %s", e)
        raise TimeoutError(
            message="Request timed out",
            suggestion="Try increasing the timeout in config",
            original_error=e,
        ) from e
    except httpx.ConnectError as e:
        logger.debug("Connection error: %s", e)
        raise NetworkError(
            message=f"Failed to connect: {e}",
            suggestion="Check your internet connection and API URL",
            original_error=e,
        ) from e
    except httpx.RequestError as e:
        logger.debug("Request error: %s", e)
        raise NetworkError(
            message=f"Network error: {e}",
            original_error=e,
        ) from e


def api_error_handler(func: Callable[P, T]) -> Callable[P, T]:
    """Decorator to wrap API calls with error handling."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with handle_api_errors():
            return func(*args, **kwargs)

    return wrapper


def async_api_error_handler(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to wrap async API calls with error handling."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except httpx.HTTPStatusError as e:
            try:
                error_body = e.response.json()
            except Exception:
                error_body = e.response.text

            logger.debug("API error: status=%d, body=%s", e.response.status_code, error_body)
            raise parse_api_error(
                status_code=e.response.status_code,
                error_body=error_body,
                original_error=e,
            ) from e
        except httpx.TimeoutException as e:
            logger.debug("Timeout error: %s", e)
            raise TimeoutError(
                message="Request timed out",
                suggestion="Try increasing the timeout in config",
                original_error=e,
            ) from e
        except httpx.ConnectError as e:
            logger.debug("Connection error: %s", e)
            raise NetworkError(
                message=f"Failed to connect: {e}",
                suggestion="Check your internet connection and API URL",
                original_error=e,
            ) from e
        except httpx.RequestError as e:
            logger.debug("Request error: %s", e)
            raise NetworkError(
                message=f"Network error: {e}",
                original_error=e,
            ) from e

    return wrapper


__all__ = [
    "parse_api_error",
    "handle_api_errors",
    "api_error_handler",
    "async_api_error_handler",
]
