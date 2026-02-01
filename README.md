# Unrealon SDK

Python SDK for the Unrealon platform. Provides service registration, real-time logging, and metrics.

## Installation

```bash
pip install unrealon
```

## Quick Start

```python
from unrealon import ServiceClient

with ServiceClient(
    api_key="your-api-key",
    service_name="my-service",
) as client:

    for item in items:
        process(item)
        client.increment_processed()
        client.info(f"Processed item {item.id}")
```

## Configuration

### Environment Variables

```bash
export UNREALON_API_KEY=your-api-key
export UNREALON_SERVICE_NAME=my-service
```

### Direct Configuration

```python
client = ServiceClient(
    api_key="your-api-key",
    service_name="my-service",
)
```

## Features

### Registration & Lifecycle

```python
# Context manager (recommended)
with ServiceClient(api_key="...", service_name="...") as client:
    # Auto-registered on enter, auto-deregistered on exit
    print(f"Service ID: {client.service_id}")

# Manual control
client = ServiceClient(api_key="...", service_name="...")
client.start()
# ... work ...
client.stop()
```

### Logging

The SDK provides a powerful logging system with three outputs:
- **Rich console** - Beautiful colored output with tracebacks
- **File** - Rotating log files in `logs/` directory
- **gRPC cloud** - Real-time logs to Unrealon platform

#### With ServiceClient

```python
with ServiceClient(...) as client:
    # Logs go to: Rich console + file + cloud
    client.info("Processing started", url="https://...", batch_size=100)
    client.warning("Rate limited", retry_after=60)
    client.error("Failed to parse", error_code=500)

    # Access the logger directly for more control
    client.logger.debug("Debug info", internal_state="ready")
```

#### Standalone Logger (without cloud)

```python
from unrealon.logging import get_logger

# Logs go to: Rich console + file
log = get_logger(__name__)
log.info("Application started", version="1.0.0")
log.error("Connection failed", host="db.example.com", port=5432)

# Exception logging with full traceback
try:
    risky_operation()
except Exception:
    log.exception("Operation failed", context="startup")
```

#### Configuration

```python
from unrealon.logging import get_logger, LogConfig, setup_logging

# Custom logger
log = get_logger(
    name="myapp",
    level="DEBUG",
    log_to_file=True,
    log_to_console=True,
    use_rich=True,
)

# Global setup
setup_logging(LogConfig(
    level="INFO",
    log_to_file=True,
    app_name="myapp",
))
```

Log files are written to `logs/` in your project root (auto-detected via `pyproject.toml`, `.git`, etc.).

### Metrics

Track processing stats:

```python
with ServiceClient(...) as client:
    for item in items:
        try:
            process(item)
            client.increment_processed()
        except Exception as e:
            client.increment_errors()
            client.error(f"Failed: {e}")
```

## Complete Example

```python
#!/usr/bin/env python3
"""Example service using Unrealon SDK."""

import random
import time
from unrealon import ServiceClient


def run_service():
    with ServiceClient(
        api_key="your-api-key",
        service_name="example-service",
    ) as client:

        print(f"Service registered: {client.service_id}")

        for i in range(10):
            # Simulate work
            items = random.randint(1, 10)
            client.increment_processed(items)
            client.info(f"Processed {items} items")

            if random.random() < 0.1:
                client.increment_errors()
                client.error("Random error occurred")

            time.sleep(1)

    print("Service stopped")


if __name__ == "__main__":
    run_service()
```

## Async Support

```python
import asyncio
from unrealon import AsyncServiceClient


async def main():
    async with AsyncServiceClient(
        api_key="your-api-key",
        service_name="async-service",
    ) as client:

        for i in range(10):
            client.info(f"Processing step {i}")
            client.increment_processed()
            await asyncio.sleep(1)


asyncio.run(main())
```

## Error Handling

```python
from unrealon import (
    UnrealonError,
    AuthenticationError,
    RegistrationError,
)

try:
    with ServiceClient(...) as client:
        pass
except AuthenticationError:
    print("Invalid API key")
except RegistrationError:
    print("Registration failed")
except UnrealonError:
    print("SDK error")
```

## License

MIT
