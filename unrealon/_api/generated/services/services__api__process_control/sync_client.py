from __future__ import annotations

import httpx

from .models import (
    CancelJobResponse,
    ProcessControlRequestRequest,
    ProcessControlResponse,
    ProcessJobDetail,
)


class SyncServicesProcessControlAPI:
    """Synchronous API endpoints for Process Control."""

    def __init__(self, client: httpx.Client):
        """Initialize sync sub-client with shared httpx client."""
        self._client = client

    def services_control_active_job_retrieve(self, service_id: str) -> ProcessJobDetail:
        """
        Get active job for service

        Get the currently active (pending/running) job for a service.
        """
        url = f"/api/services/control/{service_id}/active-job/"
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


    def services_control_restart_create(
        self,
        service_id: str,
        data: ProcessControlRequestRequest,
    ) -> ProcessControlResponse:
        """
        Restart a service

        Restart a service (stop + start). Supports graceful shutdown.
        """
        url = f"/api/services/control/{service_id}/restart/"
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
        return ProcessControlResponse.model_validate(response.json())


    def services_control_start_create(
        self,
        service_id: str,
        data: ProcessControlRequestRequest,
    ) -> ProcessControlResponse:
        """
        Start a service

        Start a service process via RQ job. Returns immediately with job ID.
        """
        url = f"/api/services/control/{service_id}/start/"
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
        return ProcessControlResponse.model_validate(response.json())


    def services_control_stop_create(
        self,
        service_id: str,
        data: ProcessControlRequestRequest,
    ) -> ProcessControlResponse:
        """
        Stop a service

        Stop a service process. Supports graceful shutdown.
        """
        url = f"/api/services/control/{service_id}/stop/"
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
        return ProcessControlResponse.model_validate(response.json())


    def services_control_jobs_cancel_create(self, job_id: str) -> CancelJobResponse:
        """
        Cancel a process job

        Cancel a pending or running process job using cooperative cancellation.
        """
        url = f"/api/services/control/jobs/{job_id}/cancel/"
        response = self._client.post(url)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return CancelJobResponse.model_validate(response.json())


