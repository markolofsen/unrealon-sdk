from __future__ import annotations

import httpx

from .models import (
    CommandAckRequest,
    CommandAckResponse,
    LogBatchRequest,
    LogBatchResponse,
    Service,
    ServiceHeartbeatRequest,
    ServiceHeartbeatResponse,
    ServiceRegistrationRequest,
    ServiceRegistrationResponse,
    ServiceRequest,
)


class SyncServicesServiceSdkAPI:
    """Synchronous API endpoints for Service SDK."""

    def __init__(self, client: httpx.Client):
        """Initialize sync sub-client with shared httpx client."""
        self._client = client

    def services_commands_ack_create(
        self,
        id: str,
        data: CommandAckRequest,
    ) -> CommandAckResponse:
        """
        Acknowledge command

        Acknowledge command from service SDK
        """
        url = f"/api/services/commands/{id}/ack/"
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
        return CommandAckResponse.model_validate(response.json())


    def services_services_deregister_create(self, id: str, data: ServiceRequest) -> Service:
        """
        Deregister service

        Deregister service from SDK (on shutdown)
        """
        url = f"/api/services/services/{id}/deregister/"
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
        return Service.model_validate(response.json())


    def services_services_heartbeat_create(
        self,
        id: str,
        data: ServiceHeartbeatRequest,
    ) -> ServiceHeartbeatResponse:
        """
        Send heartbeat

        Send heartbeat from service SDK
        """
        url = f"/api/services/services/{id}/heartbeat/"
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
        return ServiceHeartbeatResponse.model_validate(response.json())


    def services_services_logs_batch_create(
        self,
        service_id: str,
        data: LogBatchRequest,
    ) -> LogBatchResponse:
        """
        Submit log batch

        Submit batch of log entries from service SDK
        """
        url = f"/api/services/services/{service_id}/logs/batch/"
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
        return LogBatchResponse.model_validate(response.json())


    def services_services_register_create(
        self,
        data: ServiceRegistrationRequest,
    ) -> ServiceRegistrationResponse:
        """
        Register service

        Register or re-register a service from SDK
        """
        url = "/api/services/services/register/"
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
        return ServiceRegistrationResponse.model_validate(response.json())


