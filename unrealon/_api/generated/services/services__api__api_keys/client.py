from __future__ import annotations

import httpx

from .models import (
    ApiKey,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    PaginatedApiKeyList,
    PatchedApiKeyUpdateRequest,
)


class ServicesApiKeysAPI:
    """API endpoints for API Keys."""

    def __init__(self, client: httpx.AsyncClient):
        """Initialize sub-client with shared httpx client."""
        self._client = client

    async def services_api_keys_list(
        self,
        ordering: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
    ) -> list[PaginatedApiKeyList]:
        """
        List API keys

        ViewSet for API key management. Endpoints: - GET /api/api-keys/ - List
        all API keys - POST /api/api-keys/ - Create new API key - GET
        /api/api-keys/{id}/ - Get API key details - PATCH /api/api-keys/{id}/ -
        Update API key - DELETE /api/api-keys/{id}/ - Delete API key - POST
        /api/api-keys/{id}/revoke/ - Revoke API key - POST
        /api/api-keys/{id}/regenerate/ - Regenerate API key
        """
        url = "/api/services/api-keys/"
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
        return PaginatedApiKeyList.model_validate(response.json())


    async def services_api_keys_create(
        self,
        data: ApiKeyCreateRequest,
    ) -> ApiKeyCreateResponse:
        """
        Create API key

        Create new API key. The full key is only shown once!
        """
        url = "/api/services/api-keys/"
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
        return ApiKeyCreateResponse.model_validate(response.json())


    async def services_api_keys_retrieve(self, id: str) -> ApiKey:
        """
        Get API key details

        ViewSet for API key management. Endpoints: - GET /api/api-keys/ - List
        all API keys - POST /api/api-keys/ - Create new API key - GET
        /api/api-keys/{id}/ - Get API key details - PATCH /api/api-keys/{id}/ -
        Update API key - DELETE /api/api-keys/{id}/ - Delete API key - POST
        /api/api-keys/{id}/revoke/ - Revoke API key - POST
        /api/api-keys/{id}/regenerate/ - Regenerate API key
        """
        url = f"/api/services/api-keys/{id}/"
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
        return ApiKey.model_validate(response.json())


    async def services_api_keys_partial_update(
        self,
        id: str,
        data: PatchedApiKeyUpdateRequest | None = None,
    ) -> ApiKey:
        """
        Update API key

        Update API key settings.
        """
        url = f"/api/services/api-keys/{id}/"
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
        return ApiKey.model_validate(response.json())


    async def services_api_keys_destroy(self, id: str) -> None:
        """
        Delete API key

        ViewSet for API key management. Endpoints: - GET /api/api-keys/ - List
        all API keys - POST /api/api-keys/ - Create new API key - GET
        /api/api-keys/{id}/ - Get API key details - PATCH /api/api-keys/{id}/ -
        Update API key - DELETE /api/api-keys/{id}/ - Delete API key - POST
        /api/api-keys/{id}/revoke/ - Revoke API key - POST
        /api/api-keys/{id}/regenerate/ - Regenerate API key
        """
        url = f"/api/services/api-keys/{id}/"
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


    async def services_api_keys_regenerate_create(self, id: str) -> ApiKeyCreateResponse:
        """
        Regenerate API key

        Regenerate API key with new secret
        """
        url = f"/api/services/api-keys/{id}/regenerate/"
        response = await self._client.post(url)
        if not response.is_success:
            try:
                error_body = response.json()
            except Exception:
                error_body = response.text
            msg = f"{response.status_code}: {error_body}"
            raise httpx.HTTPStatusError(
                msg, request=response.request, response=response
            )
        return ApiKeyCreateResponse.model_validate(response.json())


    async def services_api_keys_revoke_create(self, id: str) -> None:
        """
        Revoke API key

        Revoke API key (deactivate)
        """
        url = f"/api/services/api-keys/{id}/revoke/"
        response = await self._client.post(url)
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


