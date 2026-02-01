from __future__ import annotations

import httpx

from .models import (
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


