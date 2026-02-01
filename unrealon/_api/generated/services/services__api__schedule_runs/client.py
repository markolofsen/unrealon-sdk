from __future__ import annotations

import httpx

from .models import (
    PaginatedScheduleRunList,
    ScheduleRunDetail,
)


class ServicesScheduleRunsAPI:
    """API endpoints for Schedule Runs."""

    def __init__(self, client: httpx.AsyncClient):
        """Initialize sub-client with shared httpx client."""
        self._client = client

    async def services_schedule_runs_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedScheduleRunList]:
        """
        List schedule runs

        ViewSet for schedule runs (read-only). Endpoints: - GET
        /api/services/schedule-runs/ - List all runs - GET
        /api/services/schedule-runs/{id}/ - Get run details
        """
        url = "/api/services/schedule-runs/"
        _params = {
            "ordering": ordering if ordering is not None else None,
            "page": page if page is not None else None,
            "page_size": page_size if page_size is not None else None,
            "search": search if search is not None else None,
        }
        response = await self._client.get(url, params=_params)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return PaginatedScheduleRunList.model_validate(response.json())


    async def services_schedule_runs_retrieve(self, id: str) -> ScheduleRunDetail:
        """
        Get schedule run details

        ViewSet for schedule runs (read-only). Endpoints: - GET
        /api/services/schedule-runs/ - List all runs - GET
        /api/services/schedule-runs/{id}/ - Get run details
        """
        url = f"/api/services/schedule-runs/{id}/"
        response = await self._client.get(url)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ScheduleRunDetail.model_validate(response.json())


