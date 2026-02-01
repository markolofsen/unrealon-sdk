"""HTTP client factory and base service classes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

from .._version import __version__

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .._config import UnrealonConfig


class HTTPClientFactory:
    """
    Factory for creating configured httpx clients.

    Creates clients with:
    - Base URL from config
    - API key authentication (Api-Key header)
    - Configured timeout
    """

    def __init__(self, config: UnrealonConfig):
        self._config = config

    def _get_headers(self) -> dict[str, str]:
        """Build request headers with API key authentication."""
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "X-API-Key": self._config.api_key,
            "Content-Type": "application/json",
            "User-Agent": f"unrealon-sdk/{__version__} ({self._config.service_name})",
        }

    def create_sync_client(self) -> httpx.Client:
        """Create a synchronous HTTP client."""
        logger.debug(
            "Creating sync HTTP client: base_url=%s, timeout=%s",
            self._config.api_url,
            self._config.timeout,
        )
        return httpx.Client(
            base_url=self._config.api_url,
            headers=self._get_headers(),
            timeout=self._config.timeout,
        )

    def create_async_client(self) -> httpx.AsyncClient:
        """Create an asynchronous HTTP client."""
        logger.debug(
            "Creating async HTTP client: base_url=%s, timeout=%s",
            self._config.api_url,
            self._config.timeout,
        )
        return httpx.AsyncClient(
            base_url=self._config.api_url,
            headers=self._get_headers(),
            timeout=self._config.timeout,
        )


class BaseService:
    """
    Base class for synchronous SDK services.

    Provides:
    - HTTP client via HTTPClientFactory
    - Access to SDK config
    """

    def __init__(self, config: UnrealonConfig):
        self._config = config
        self._factory = HTTPClientFactory(config)
        self._http_client = self._factory.create_sync_client()

    @property
    def http_client(self) -> httpx.Client:
        """Access the underlying HTTP client."""
        return self._http_client

    @property
    def config(self) -> UnrealonConfig:
        """Access the SDK configuration."""
        return self._config

    def close(self):
        """Close HTTP client."""
        self._http_client.close()


class AsyncBaseService:
    """
    Base class for asynchronous SDK services.

    Provides:
    - Async HTTP client via HTTPClientFactory
    - Access to SDK config
    """

    def __init__(self, config: UnrealonConfig):
        self._config = config
        self._factory = HTTPClientFactory(config)
        self._http_client = self._factory.create_async_client()

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Access the underlying HTTP client."""
        return self._http_client

    @property
    def config(self) -> UnrealonConfig:
        """Access the SDK configuration."""
        return self._config

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()


__all__ = [
    "HTTPClientFactory",
    "BaseService",
    "AsyncBaseService",
]
