from __future__ import annotations

import httpx

from .models import (
    PaginatedProcessJobList,
    ProcessJobDetail,
)


class SyncServicesProcessJobsAPI:
    """Synchronous API endpoints for Process Jobs."""

    def __init__(self, client: httpx.Client):
        """Initialize sync sub-client with shared httpx client."""
        self._client = client

    def services_process_jobs_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedProcessJobList]:
        """
        List process jobs

        ViewSet for viewing process jobs. Process jobs track start/stop/restart
        operations on services. All operations are async via RQ jobs. Endpoints:
        - GET /api/services/process-jobs/ - List all process jobs - GET
        /api/services/process-jobs/{id}/ - Get job details - GET
        /api/services/process-jobs/by-service/{service_id}/ - Jobs for a service
        """
        url = "/api/services/process-jobs/"
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
        return PaginatedProcessJobList.model_validate(response.json())


    def services_process_jobs_retrieve(self, id: str) -> ProcessJobDetail:
        """
        Get process job details

        ViewSet for viewing process jobs. Process jobs track start/stop/restart
        operations on services. All operations are async via RQ jobs. Endpoints:
        - GET /api/services/process-jobs/ - List all process jobs - GET
        /api/services/process-jobs/{id}/ - Get job details - GET
        /api/services/process-jobs/by-service/{service_id}/ - Jobs for a service
        """
        url = f"/api/services/process-jobs/{id}/"
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
        return ProcessJobDetail.model_validate(response.json())


    def services_process_jobs_by_service_list(
        self,
        service_id: str,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedProcessJobList]:
        """
        Get process jobs for a service

        Get process jobs for a specific service.
        """
        url = f"/api/services/process-jobs/by-service/{service_id}/"
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
        return PaginatedProcessJobList.model_validate(response.json())


