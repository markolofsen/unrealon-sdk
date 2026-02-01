from __future__ import annotations

import httpx

from .models import (
    Command,
    PaginatedCommandList,
)


class SyncServicesServiceCommandsAPI:
    """Synchronous API endpoints for Service Commands."""

    def __init__(self, client: httpx.Client):
        """Initialize sync sub-client with shared httpx client."""
        self._client = client

    def services_commands_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedCommandList]:
        """
        List commands

        ViewSet for service commands. Endpoints: - GET /api/services/commands/ -
        List all commands - GET /api/services/commands/{id}/ - Get command
        details - POST /api/services/{service_id}/commands/ - Create command
        (via ServiceViewSet) - GET /api/services/{service_id}/commands/pending/
        - Get pending commands (SDK) - POST /api/commands/{id}/ack/ -
        Acknowledge command (SDK)
        """
        url = "/api/services/commands/"
        _params = {
            "ordering": ordering if ordering is not None else None,
            "page": page if page is not None else None,
            "page_size": page_size if page_size is not None else None,
            "search": search if search is not None else None,
        }
        response = self._client.get(url, params=_params)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return PaginatedCommandList.model_validate(response.json())


    def services_commands_retrieve(self, id: str) -> Command:
        """
        Get command details

        ViewSet for service commands. Endpoints: - GET /api/services/commands/ -
        List all commands - GET /api/services/commands/{id}/ - Get command
        details - POST /api/services/{service_id}/commands/ - Create command
        (via ServiceViewSet) - GET /api/services/{service_id}/commands/pending/
        - Get pending commands (SDK) - POST /api/commands/{id}/ack/ -
        Acknowledge command (SDK)
        """
        url = f"/api/services/commands/{id}/"
        response = self._client.get(url)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return Command.model_validate(response.json())


