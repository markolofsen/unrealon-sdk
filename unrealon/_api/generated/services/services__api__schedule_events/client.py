from __future__ import annotations

import httpx

from .models import (
    PaginatedScheduleEventList,
    ScheduleEvent,
)


class ServicesScheduleEventsAPI:
    """API endpoints for Schedule Events."""

    def __init__(self, client: httpx.AsyncClient):
        """Initialize sub-client with shared httpx client."""
        self._client = client

    async def services_schedule_events_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedScheduleEventList]:
        """
        List schedule events

        ViewSet for schedule events (read-only). Endpoints: - GET
        /api/services/schedule-events/ - List all events - GET
        /api/services/schedule-events/{id}/ - Get event details
        """
        url = "/api/services/schedule-events/"
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
        return PaginatedScheduleEventList.model_validate(response.json())


    async def services_schedule_events_retrieve(self, id: str) -> ScheduleEvent:
        """
        Get schedule event details

        ViewSet for schedule events (read-only). Endpoints: - GET
        /api/services/schedule-events/ - List all events - GET
        /api/services/schedule-events/{id}/ - Get event details
        """
        url = f"/api/services/schedule-events/{id}/"
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
        return ScheduleEvent.model_validate(response.json())


