from __future__ import annotations

import httpx

from .models import (
    PaginatedScheduleEventList,
    PaginatedScheduleList,
    PaginatedScheduleRunList,
    PatchedScheduleCreateRequest,
    ScheduleCreate,
    ScheduleCreateRequest,
    ScheduleDetail,
    ScheduleToggleRequest,
    ScheduleTriggerRequest,
)


class ServicesSchedulesAPI:
    """API endpoints for Schedules."""

    def __init__(self, client: httpx.AsyncClient):
        """Initialize sub-client with shared httpx client."""
        self._client = client

    async def services_schedules_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedScheduleList]:
        """
        List schedules

        ViewSet for schedule management. Endpoints: - GET
        /api/services/schedules/ - List all schedules - POST
        /api/services/schedules/ - Create schedule - GET
        /api/services/schedules/{id}/ - Get schedule details - PUT/PATCH
        /api/services/schedules/{id}/ - Update schedule - DELETE
        /api/services/schedules/{id}/ - Delete schedule - POST
        /api/services/schedules/{id}/toggle/ - Enable/disable schedule - POST
        /api/services/schedules/{id}/trigger/ - Manually trigger schedule - GET
        /api/services/schedules/{id}/runs/ - Get schedule runs - GET
        /api/services/schedules/{id}/events/ - Get schedule events
        """
        url = "/api/services/schedules/"
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
        return PaginatedScheduleList.model_validate(response.json())


    async def services_schedules_create(self, data: ScheduleCreateRequest) -> ScheduleCreate:
        """
        Create schedule

        ViewSet for schedule management. Endpoints: - GET
        /api/services/schedules/ - List all schedules - POST
        /api/services/schedules/ - Create schedule - GET
        /api/services/schedules/{id}/ - Get schedule details - PUT/PATCH
        /api/services/schedules/{id}/ - Update schedule - DELETE
        /api/services/schedules/{id}/ - Delete schedule - POST
        /api/services/schedules/{id}/toggle/ - Enable/disable schedule - POST
        /api/services/schedules/{id}/trigger/ - Manually trigger schedule - GET
        /api/services/schedules/{id}/runs/ - Get schedule runs - GET
        /api/services/schedules/{id}/events/ - Get schedule events
        """
        url = "/api/services/schedules/"
        response = await self._client.post(url, json=data.model_dump(exclude_unset=True))
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ScheduleCreate.model_validate(response.json())


    async def services_schedules_retrieve(self, id: str) -> ScheduleDetail:
        """
        Get schedule details

        ViewSet for schedule management. Endpoints: - GET
        /api/services/schedules/ - List all schedules - POST
        /api/services/schedules/ - Create schedule - GET
        /api/services/schedules/{id}/ - Get schedule details - PUT/PATCH
        /api/services/schedules/{id}/ - Update schedule - DELETE
        /api/services/schedules/{id}/ - Delete schedule - POST
        /api/services/schedules/{id}/toggle/ - Enable/disable schedule - POST
        /api/services/schedules/{id}/trigger/ - Manually trigger schedule - GET
        /api/services/schedules/{id}/runs/ - Get schedule runs - GET
        /api/services/schedules/{id}/events/ - Get schedule events
        """
        url = f"/api/services/schedules/{id}/"
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
        return ScheduleDetail.model_validate(response.json())


    async def services_schedules_update(
        self,
        id: str,
        data: ScheduleCreateRequest,
    ) -> ScheduleCreate:
        """
        Update schedule

        ViewSet for schedule management. Endpoints: - GET
        /api/services/schedules/ - List all schedules - POST
        /api/services/schedules/ - Create schedule - GET
        /api/services/schedules/{id}/ - Get schedule details - PUT/PATCH
        /api/services/schedules/{id}/ - Update schedule - DELETE
        /api/services/schedules/{id}/ - Delete schedule - POST
        /api/services/schedules/{id}/toggle/ - Enable/disable schedule - POST
        /api/services/schedules/{id}/trigger/ - Manually trigger schedule - GET
        /api/services/schedules/{id}/runs/ - Get schedule runs - GET
        /api/services/schedules/{id}/events/ - Get schedule events
        """
        url = f"/api/services/schedules/{id}/"
        response = await self._client.put(url, json=data.model_dump(exclude_unset=True))
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ScheduleCreate.model_validate(response.json())


    async def services_schedules_partial_update(
        self,
        id: str,
        data: PatchedScheduleCreateRequest | None = None,
    ) -> ScheduleCreate:
        """
        Partial update schedule

        ViewSet for schedule management. Endpoints: - GET
        /api/services/schedules/ - List all schedules - POST
        /api/services/schedules/ - Create schedule - GET
        /api/services/schedules/{id}/ - Get schedule details - PUT/PATCH
        /api/services/schedules/{id}/ - Update schedule - DELETE
        /api/services/schedules/{id}/ - Delete schedule - POST
        /api/services/schedules/{id}/toggle/ - Enable/disable schedule - POST
        /api/services/schedules/{id}/trigger/ - Manually trigger schedule - GET
        /api/services/schedules/{id}/runs/ - Get schedule runs - GET
        /api/services/schedules/{id}/events/ - Get schedule events
        """
        url = f"/api/services/schedules/{id}/"
        _json = data.model_dump(exclude_unset=True) if data else None
        response = await self._client.patch(url, json=_json)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ScheduleCreate.model_validate(response.json())


    async def services_schedules_destroy(self, id: str) -> None:
        """
        Delete schedule

        ViewSet for schedule management. Endpoints: - GET
        /api/services/schedules/ - List all schedules - POST
        /api/services/schedules/ - Create schedule - GET
        /api/services/schedules/{id}/ - Get schedule details - PUT/PATCH
        /api/services/schedules/{id}/ - Update schedule - DELETE
        /api/services/schedules/{id}/ - Delete schedule - POST
        /api/services/schedules/{id}/toggle/ - Enable/disable schedule - POST
        /api/services/schedules/{id}/trigger/ - Manually trigger schedule - GET
        /api/services/schedules/{id}/runs/ - Get schedule runs - GET
        /api/services/schedules/{id}/events/ - Get schedule events
        """
        url = f"/api/services/schedules/{id}/"
        response = await self._client.delete(url)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return None


    async def services_schedules_events_list(
        self,
        id: str,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedScheduleEventList]:
        """
        Get schedule events

        Get event log for a schedule
        """
        url = f"/api/services/schedules/{id}/events/"
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


    async def services_schedules_runs_list(
        self,
        id: str,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedScheduleRunList]:
        """
        Get schedule runs

        Get execution history for a schedule
        """
        url = f"/api/services/schedules/{id}/runs/"
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


    async def services_schedules_toggle_create(
        self,
        id: str,
        data: ScheduleToggleRequest,
    ) -> ScheduleDetail:
        """
        Toggle schedule

        Enable or disable a schedule
        """
        url = f"/api/services/schedules/{id}/toggle/"
        response = await self._client.post(url, json=data.model_dump(exclude_unset=True))
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ScheduleDetail.model_validate(response.json())


    async def services_schedules_trigger_create(
        self,
        id: str,
        data: ScheduleTriggerRequest,
    ) -> None:
        """
        Trigger schedule

        Manually trigger a schedule execution
        """
        url = f"/api/services/schedules/{id}/trigger/"
        response = await self._client.post(url, json=data.model_dump(exclude_unset=True))
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return None


