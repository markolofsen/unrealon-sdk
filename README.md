# Unrealon SDK

Python SDK for monitoring and managing services via the Unrealon platform.

## Features

- **Monitoring** — real-time service status visibility
- **Cloud Logs** — all logs accessible in the web interface
- **Control** — pause/resume/stop directly from the dashboard
- **Metrics** — counters for processed items and errors
- **Scheduling** — automatic cron-based task execution

## Installation

```bash
pip install unrealon
```

## Quick Start

### Minimal Example

```python
from unrealon import ServiceClient

with ServiceClient(api_key="pk_xxx", service_name="my-service") as client:
    client.info("Started")

    for item in items:
        process(item)
        client.increment_processed()

    client.info("Done")
```

The service will register, logs will stream to cloud, and metrics will be displayed.

### With Pause/Resume Support

```python
from unrealon import ServiceClient

with ServiceClient(api_key="pk_xxx", service_name="my-parser") as client:
    client.info("Started")

    for item in items:
        client.check_interrupt()  # Parser pauses here if Pause is clicked

        process(item)
        client.increment_processed()

    client.info("Done")
```

`check_interrupt()` does two things:
- If **Pause** was clicked — waits until Resume
- If **Stop** was clicked — raises `StopInterrupt`

## Continuous Mode

A service that waits for commands from the dashboard:

```python
import time
from unrealon import ServiceClient
from unrealon.exceptions import StopInterrupt

with ServiceClient(api_key="pk_xxx", service_name="my-parser") as client:

    def handle_run(params: dict) -> dict:
        limit = params.get("limit", 100)

        client.set_busy()
        try:
            for i in range(limit):
                client.check_interrupt()
                do_work()
                client.increment_processed()
            return {"status": "ok"}
        except StopInterrupt:
            return {"status": "stopped"}
        finally:
            client.set_idle()

    client.on_command("run", handle_run)

    # Wait for commands
    client.set_idle()
    while not client.should_stop:
        time.sleep(1)
```

Now from the dashboard you can:
- Click **Run** — executes `handle_run`
- Click **Pause** — parser stops at `check_interrupt()`
- Click **Resume** — continues from where it left off
- Click **Stop** — graceful shutdown

## API

### Logging

```python
client.debug("Debug message")
client.info("Info message", key="value")
client.warning("Warning")
client.error("Error", code=500)
```

Logs go to three places: console (Rich), file, and cloud.

### Metrics

```python
client.increment_processed()      # +1 processed
client.increment_processed(10)    # +10 processed
client.increment_errors()         # +1 error
```

### Status

```python
client.set_busy()    # Shows "Busy" in dashboard
client.set_idle()    # Shows "Idle"
```

### State

```python
client.is_paused     # True if paused
client.should_stop   # True if stop requested
client.is_connected  # True if connected to server
```

### Commands

```python
# Register handler
client.on_command("run", handle_run)
client.on_command("custom", handle_custom)

# Handler receives params and returns result
def handle_run(params: dict) -> dict:
    limit = params.get("limit", 10)
    # ... do work ...
    return {"status": "ok", "processed": 100}
```

### Schedules

Schedules run automatically based on cron expressions.
If the schedule's `action_type` matches a registered command,
the same handler is used:

```python
# This handler works for both manual Run and scheduled runs
client.on_command("run", handle_run)
```

For different behavior, register a schedule-specific handler:

```python
@client.on_schedule("process")
def handle_scheduled_process(schedule, params):
    # schedule.name, schedule.id are available
    return {"items_processed": 100}
```

## Configuration

### Via Environment Variables

```bash
export UNREALON_API_KEY=pk_xxx
export UNREALON_SERVICE_NAME=my-service
```

```python
# Picks up from env
with ServiceClient() as client:
    ...
```

### Dev Mode (Local Server)

```python
with ServiceClient(
    api_key="dk_xxx",
    service_name="my-service",
    dev_mode=True,  # Connects to localhost:50051
) as client:
    ...
```

## Exceptions

```python
from unrealon.exceptions import (
    StopInterrupt,        # Stop requested (inherits BaseException!)
    UnrealonError,        # Base SDK error
    AuthenticationError,  # Bad API key
    RegistrationError,    # Can't register
)

try:
    with ServiceClient(...) as client:
        for item in items:
            client.check_interrupt()
            process(item)
except StopInterrupt:
    print("Stopped by command")
```

**Important**: `StopInterrupt` inherits from `BaseException`, not `Exception`.
This means `except Exception` won't catch it — by design, so generic
error handlers don't swallow the stop command.

## Standalone Logger

You can use the logger separately from the SDK:

```python
from unrealon.logging import get_logger

log = get_logger("myapp")
log.info("Starting", version="1.0")
log.error("Failed", error="connection timeout")
```

Logs go to console and file (without cloud).
