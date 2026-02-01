from __future__ import annotations

import httpx

from .models import (
    SendCommandRequest,
    SendCommandResponse,
    ServiceControlRequest,
)


class SyncServicesServiceControlAPI:
    """Synchronous API endpoints for Service Control."""

    def __init__(self, client: httpx.Client):
        """Initialize sync sub-client with shared httpx client."""
        self._client = client

    def services_services_control_create(self, id: str, data: ServiceControlRequest) -> None:
        """
        Control service

        Send control command to service
        """
        url = f"/api/services/services/{id}/control/"
        response = self._client.post(url, json=data.model_dump(exclude_unset=True))
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )


    def services_services_send_command_create(
        self,
        id: str,
        data: SendCommandRequest,
    ) -> SendCommandResponse:
        """
        Send command via gRPC

        Send command directly to connected service via gRPC unary RPC. Commands:
        - **run**: Start a task (e.g., parsing). Params like `{"limit": 10}` are
        passed to handler. - **start**: Alias for run. - **pause**: Pause the
        service. Service will stop processing after current item. - **resume**:
        Resume a paused service. - **stop**: Graceful shutdown. Service will
        finish current work and exit. - **restart**: Stop then run. Equivalent
        to stop followed by run. The service must be connected via gRPC
        bidirectional stream for commands to be delivered. Returns 400 if
        service is not connected.
        """
        url = f"/api/services/services/{id}/send_command/"
        response = self._client.post(url, json=data.model_dump(exclude_unset=True))
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return SendCommandResponse.model_validate(response.json())


