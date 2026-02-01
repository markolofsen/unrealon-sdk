from __future__ import annotations

from typing import Any

import httpx

from .helpers import APILogger, LoggerConfig, RetryAsyncClient, RetryConfig
from .services__api__api_keys import ServicesApiKeysAPI
from .services__api__process_control import ServicesProcessControlAPI
from .services__api__process_jobs import ServicesProcessJobsAPI
from .services__api__schedule_events import ServicesScheduleEventsAPI
from .services__api__schedule_runs import ServicesScheduleRunsAPI
from .services__api__schedules import ServicesSchedulesAPI
from .services__api__service_commands import ServicesServiceCommandsAPI
from .services__api__service_control import ServicesServiceControlAPI
from .services__api__service_logs import ServicesServiceLogsAPI
from .services__api__service_sdk import ServicesServiceSdkAPI
from .services__api__services import ServicesServicesAPI


class APIClient:
    """
    Async API client for Unrealon API.

    Usage:
        >>> async with APIClient(base_url='https://api.example.com') as client:
        ...     users = await client.users.list()
        ...     post = await client.posts.create(data=new_post)
        >>>
        >>> # With retry configuration
        >>> retry = RetryConfig(max_attempts=5, min_wait=2.0)
        >>> async with APIClient('https://api.example.com', retry_config=retry) as c:
        ...     users = await c.users.list()
    """

    def __init__(
        self,
        base_url: str,
        logger_config: LoggerConfig | None = None,
        retry_config: RetryConfig | None = None,
        **kwargs: Any,
    ):
        """
        Initialize API client.

        Args:
            base_url: Base API URL (e.g., 'https://api.example.com')
            logger_config: Logger configuration (None to disable logging)
            retry_config: Retry configuration (None to disable retry)
            **kwargs: Additional httpx.AsyncClient kwargs
        """
        self.base_url = base_url.rstrip('/')

        # Create HTTP client with or without retry
        if retry_config is not None:
            self._client = RetryAsyncClient(
                base_url=self.base_url,
                retry_config=retry_config,
                **kwargs,
            )
        else:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                **kwargs,
            )

        # Initialize logger
        self.logger: APILogger | None = None
        if logger_config is not None:
            self.logger = APILogger(logger_config)

        # Initialize sub-clients
        self.services_api_keys = ServicesApiKeysAPI(self._client)
        self.services_process_control = ServicesProcessControlAPI(self._client)
        self.services_process_jobs = ServicesProcessJobsAPI(self._client)
        self.services_schedule_events = ServicesScheduleEventsAPI(self._client)
        self.services_schedule_runs = ServicesScheduleRunsAPI(self._client)
        self.services_schedules = ServicesSchedulesAPI(self._client)
        self.services_service_commands = ServicesServiceCommandsAPI(self._client)
        self.services_service_control = ServicesServiceControlAPI(self._client)
        self.services_service_logs = ServicesServiceLogsAPI(self._client)
        self.services_service_sdk = ServicesServiceSdkAPI(self._client)
        self.services_services = ServicesServicesAPI(self._client)

    async def __aenter__(self) -> APIClient:
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.__aexit__(*args)

    async def close(self) -> None:
        """Close HTTP client."""
        await self._client.aclose()