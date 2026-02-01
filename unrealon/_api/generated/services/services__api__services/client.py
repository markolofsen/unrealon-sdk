from __future__ import annotations

import httpx

from .models import (
    ApiKey,
    PaginatedServiceList,
    PatchedServiceDetailRequest,
    Service,
    ServiceDetail,
    ServiceDetailRequest,
    ServiceRequest,
)


class ServicesServicesAPI:
    """API endpoints for Services."""

    def __init__(self, client: httpx.AsyncClient):
        """Initialize sub-client with shared httpx client."""
        self._client = client

    async def api_keys_update(self, id: str) -> ApiKey:
        """
        ViewSet for API key management. Endpoints: - GET /api/api-keys/ - List
        all API keys - POST /api/api-keys/ - Create new API key - GET
        /api/api-keys/{id}/ - Get API key details - PATCH /api/api-keys/{id}/ -
        Update API key - DELETE /api/api-keys/{id}/ - Delete API key - POST
        /api/api-keys/{id}/revoke/ - Revoke API key - POST
        /api/api-keys/{id}/regenerate/ - Regenerate API key
        """
        url = f"/api/services/api-keys/{id}/"
        response = await self._client.put(url)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ApiKey.model_validate(response.json())


    async def services_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedServiceList]:
        """
        List services

        ViewSet for service management. Endpoints: - GET /api/services/ - List
        all services - POST /api/services/ - Create service (admin only) - GET
        /api/services/{id}/ - Get service details - PUT/PATCH
        /api/services/{id}/ - Update service - DELETE /api/services/{id}/ -
        Delete service - POST /api/services/register/ - Register service (from
        SDK) - POST /api/services/{id}/heartbeat/ - Send heartbeat (from SDK) -
        POST /api/services/{id}/control/ - Send control command - POST
        /api/services/{id}/deregister/ - Deregister service
        """
        url = "/api/services/services/"
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
        return PaginatedServiceList.model_validate(response.json())


    async def services_create(self, data: ServiceRequest) -> Service:
        """
        Create service

        ViewSet for service management. Endpoints: - GET /api/services/ - List
        all services - POST /api/services/ - Create service (admin only) - GET
        /api/services/{id}/ - Get service details - PUT/PATCH
        /api/services/{id}/ - Update service - DELETE /api/services/{id}/ -
        Delete service - POST /api/services/register/ - Register service (from
        SDK) - POST /api/services/{id}/heartbeat/ - Send heartbeat (from SDK) -
        POST /api/services/{id}/control/ - Send control command - POST
        /api/services/{id}/deregister/ - Deregister service
        """
        url = "/api/services/services/"
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
        return Service.model_validate(response.json())


    async def services_retrieve(self, id: str) -> ServiceDetail:
        """
        Get service details

        ViewSet for service management. Endpoints: - GET /api/services/ - List
        all services - POST /api/services/ - Create service (admin only) - GET
        /api/services/{id}/ - Get service details - PUT/PATCH
        /api/services/{id}/ - Update service - DELETE /api/services/{id}/ -
        Delete service - POST /api/services/register/ - Register service (from
        SDK) - POST /api/services/{id}/heartbeat/ - Send heartbeat (from SDK) -
        POST /api/services/{id}/control/ - Send control command - POST
        /api/services/{id}/deregister/ - Deregister service
        """
        url = f"/api/services/services/{id}/"
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
        return ServiceDetail.model_validate(response.json())


    async def services_update(self, id: str, data: ServiceDetailRequest) -> ServiceDetail:
        """
        Update service

        ViewSet for service management. Endpoints: - GET /api/services/ - List
        all services - POST /api/services/ - Create service (admin only) - GET
        /api/services/{id}/ - Get service details - PUT/PATCH
        /api/services/{id}/ - Update service - DELETE /api/services/{id}/ -
        Delete service - POST /api/services/register/ - Register service (from
        SDK) - POST /api/services/{id}/heartbeat/ - Send heartbeat (from SDK) -
        POST /api/services/{id}/control/ - Send control command - POST
        /api/services/{id}/deregister/ - Deregister service
        """
        url = f"/api/services/services/{id}/"
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
        return ServiceDetail.model_validate(response.json())


    async def services_partial_update(
        self,
        id: str,
        data: PatchedServiceDetailRequest | None = None,
    ) -> ServiceDetail:
        """
        Partial update service

        ViewSet for service management. Endpoints: - GET /api/services/ - List
        all services - POST /api/services/ - Create service (admin only) - GET
        /api/services/{id}/ - Get service details - PUT/PATCH
        /api/services/{id}/ - Update service - DELETE /api/services/{id}/ -
        Delete service - POST /api/services/register/ - Register service (from
        SDK) - POST /api/services/{id}/heartbeat/ - Send heartbeat (from SDK) -
        POST /api/services/{id}/control/ - Send control command - POST
        /api/services/{id}/deregister/ - Deregister service
        """
        url = f"/api/services/services/{id}/"
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
        return ServiceDetail.model_validate(response.json())


    async def services_destroy(self, id: str) -> None:
        """
        Delete service

        ViewSet for service management. Endpoints: - GET /api/services/ - List
        all services - POST /api/services/ - Create service (admin only) - GET
        /api/services/{id}/ - Get service details - PUT/PATCH
        /api/services/{id}/ - Update service - DELETE /api/services/{id}/ -
        Delete service - POST /api/services/register/ - Register service (from
        SDK) - POST /api/services/{id}/heartbeat/ - Send heartbeat (from SDK) -
        POST /api/services/{id}/control/ - Send control command - POST
        /api/services/{id}/deregister/ - Deregister service
        """
        url = f"/api/services/services/{id}/"
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


    async def services_commands_retrieve(self, service_id: str) -> None:
        """
        Get pending commands for service.
        """
        url = f"/api/services/services/{service_id}/commands/"
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
        return None


