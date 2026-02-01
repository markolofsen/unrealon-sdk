"""
Service registration via gRPC unary RPC.

Handles Register and Deregister operations with sync/async variants.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import socket
import sys
from typing import TYPE_CHECKING, Any

from grpc import aio

from ._config import GRPCServiceConfig
from .generated import unrealon_pb2

if TYPE_CHECKING:
    from .generated import unrealon_pb2_grpc

logger = logging.getLogger(__name__)


def get_sdk_version() -> str:
    """Get SDK version."""
    try:
        from .._version import __version__

        return __version__
    except ImportError:
        return "unknown"


class RegistrationManager:
    """Manages service registration and deregistration.

    Provides both sync and async variants for Register and Deregister RPC.
    """

    __slots__ = ("_config", "_service_id")

    def __init__(self, config: GRPCServiceConfig) -> None:
        """
        Initialize registration manager.

        Args:
            config: Service configuration
        """
        self._config = config
        self._service_id: str | None = None

    @property
    def service_id(self) -> str | None:
        """Get registered service ID."""
        return self._service_id

    @service_id.setter
    def service_id(self, value: str | None) -> None:
        """Set service ID."""
        self._service_id = value

    async def register_async(
        self,
        stub: unrealon_pb2_grpc.UnrealonServiceStub,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Register service via unary RPC (async).

        Args:
            stub: gRPC stub
            description: Service description
            metadata: Additional metadata

        Returns:
            service_id from server

        Raises:
            Exception: If registration fails
            aio.AioRpcError: If gRPC error occurs
        """
        request = unrealon_pb2.RegisterRequest(
            name=self._config.service_name,
            hostname=socket.gethostname(),
            pid=os.getpid(),
            description=description or self._config.description,
            source_code=self._config.source_code,
            executable_path=sys.executable,
            working_directory=os.getcwd(),
            sdk_version=get_sdk_version(),
            python_version=platform.python_version(),
        )

        auth_metadata = [("x-api-key", self._config.api_key)]

        try:
            response = await stub.Register(request, metadata=auth_metadata)

            if not response.success:
                msg = f"Registration failed: {response.message}"
                raise Exception(msg)

            self._service_id = response.service_id
            logger.info(
                "Service registered: %s (%s)",
                self._service_id,
                self._config.service_name,
            )

            return self._service_id, response.initial_config

        except aio.AioRpcError as e:
            # Convert gRPC errors to human-readable messages
            error_msg = self._format_grpc_error(e)
            logger.error("Registration failed: %s", error_msg)
            raise Exception(error_msg) from None

    def _format_grpc_error(self, e: aio.AioRpcError) -> str:
        """Convert gRPC error to human-readable message."""
        code = str(e.code()).replace("StatusCode.", "")
        details = e.details() or ""
        server = self._config.grpc_server

        # Common error translations
        if "404" in details or code == "UNIMPLEMENTED":
            return f"gRPC server at {server} returned 404. Check if gRPC service is running."
        elif code == "UNAVAILABLE":
            return f"Cannot connect to gRPC server at {server}. Check if server is running."
        elif code == "UNAUTHENTICATED":
            return f"Invalid API key for {server}. Check your credentials."
        elif code == "DEADLINE_EXCEEDED":
            return f"Connection to {server} timed out."
        elif "127.0.0.1" in details or "localhost" in details:
            return f"Connection refused to {server}. Is the gRPC server running?"
        else:
            return f"gRPC error ({code}): {details}"

    def register(
        self,
        stub: unrealon_pb2_grpc.UnrealonServiceStub,
        loop: asyncio.AbstractEventLoop | None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Register service via unary RPC (sync).

        Args:
            stub: gRPC stub
            loop: Event loop for async execution
            description: Service description
            metadata: Additional metadata

        Returns:
            service_id from server
        """
        # Create or get event loop for sync call
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop and running_loop.is_running():
            # We're in an async context, use thread-safe call
            future = asyncio.run_coroutine_threadsafe(
                self.register_async(stub, description, metadata),
                running_loop,
            )
            result = future.result(timeout=30.0)
            return result[0]  # Return service_id
        else:
            # Run in new event loop
            result = asyncio.run(self.register_async(stub, description, metadata))
            return result[0]

    async def deregister_async(
        self,
        stub: unrealon_pb2_grpc.UnrealonServiceStub,
        reason: str | None = None,
    ) -> bool:
        """
        Deregister service via unary RPC (async).

        Args:
            stub: gRPC stub
            reason: Reason for deregistration

        Returns:
            True if successful
        """
        if not self._service_id:
            # Silent return if not registered (normal state)
            logger.debug("Skipping deregister: not registered")
            return False

        request = unrealon_pb2.DeregisterRequest(
            service_id=self._service_id,
            reason=reason or "normal_shutdown",
        )

        auth_metadata = [("x-api-key", self._config.api_key)]

        try:
            response = await stub.Deregister(request, metadata=auth_metadata)

            if response.success:
                logger.info("Service deregistered: %s", self._service_id)
                self._service_id = None
                return True
            else:
                logger.error("Deregistration failed: %s", response.message)
                return False

        except aio.AioRpcError as e:
            logger.error("gRPC deregistration error: %s - %s", e.code(), e.details())
            return False

    def deregister(
        self,
        stub: unrealon_pb2_grpc.UnrealonServiceStub,
        loop: asyncio.AbstractEventLoop | None,
        reason: str | None = None,
    ) -> bool:
        """
        Deregister service via unary RPC (sync).

        Args:
            stub: gRPC stub
            loop: Event loop for async execution
            reason: Reason for deregistration

        Returns:
            True if successful
        """
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self.deregister_async(stub, reason),
                loop,
            )
            return future.result(timeout=10.0)
        else:
            try:
                return asyncio.run(self.deregister_async(stub, reason))
            except RuntimeError:
                # Event loop closed
                return False


__all__ = ["RegistrationManager", "get_sdk_version"]
