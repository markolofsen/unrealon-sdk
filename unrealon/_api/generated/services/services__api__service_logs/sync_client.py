from __future__ import annotations

import httpx

from .models import (
    PaginatedServiceLogList,
    ServiceLog,
)


class SyncServicesServiceLogsAPI:
    """Synchronous API endpoints for Service Logs."""

    def __init__(self, client: httpx.Client):
        """Initialize sync sub-client with shared httpx client."""
        self._client = client

    def services_logs_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedServiceLogList]:
        """
        List logs

        ViewSet for service logs (read-only). Endpoints: - GET
        /api/services/logs/ - List all logs (filtered) - GET
        /api/services/logs/{id}/ - Get log entry details - POST
        /api/services/{service_id}/logs/batch/ - Submit log batch (SDK)
        """
        url = "/api/services/logs/"
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
        return PaginatedServiceLogList.model_validate(response.json())


    def services_logs_retrieve(self, id: str) -> ServiceLog:
        """
        Get log entry

        ViewSet for service logs (read-only). Endpoints: - GET
        /api/services/logs/ - List all logs (filtered) - GET
        /api/services/logs/{id}/ - Get log entry details - POST
        /api/services/{service_id}/logs/batch/ - Submit log batch (SDK)
        """
        url = f"/api/services/logs/{id}/"
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
        return ServiceLog.model_validate(response.json())


