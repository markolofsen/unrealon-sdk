"""
Schedule data models for SDK.

Pydantic v2 models for schedule configuration received from server.
"""

from __future__ import annotations

import json
import zoneinfo
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ScheduleRunStatus(str, Enum):
    """Status of schedule execution."""

    UNSPECIFIED = "unspecified"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class Schedule(BaseModel):
    """
    Schedule configuration from server.

    Uses cron expressions (Unix 5-field format) for scheduling.
    """

    model_config = {"frozen": True}

    id: str
    name: str
    enabled: bool = True
    action_type: str
    action_params: dict[str, Any] = Field(default_factory=dict)

    # Cron settings
    cron_expression: str = Field(
        default="0 9 * * *",
        description="Unix cron expression (5 fields: minute hour day month weekday)",
    )
    timezone: str = Field(default="UTC")

    # Execution settings
    timeout_ms: int = Field(default=300000, description="Timeout in milliseconds (default 5 min)")
    max_retries: int = Field(default=0)
    retry_delay_ms: int = Field(default=5000)

    # Next scheduled run (from server)
    next_run_at: datetime | None = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression format."""
        if not v or not v.strip():
            return "0 9 * * *"  # Default: daily at 9:00

        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: expected 5 fields, got {len(parts)}")

        return v.strip()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string."""
        try:
            zoneinfo.ZoneInfo(v)
        except Exception:
            return "UTC"
        return v

    @classmethod
    def from_proto(cls, proto: Any) -> Schedule:
        """Create Schedule from protobuf message."""
        action_params: dict[str, Any] = {}
        if proto.action_params:
            try:
                action_params = json.loads(proto.action_params)
            except json.JSONDecodeError:
                pass

        next_run: datetime | None = None
        if proto.next_run_at:
            try:
                next_run = datetime.fromisoformat(proto.next_run_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        return cls(
            id=proto.id,
            name=proto.name,
            enabled=proto.enabled,
            action_type=proto.action_type,
            action_params=action_params,
            cron_expression=proto.cron_expression or "0 9 * * *",
            timezone=proto.timezone or "UTC",
            timeout_ms=proto.timeout_ms or 300000,
            max_retries=proto.max_retries or 0,
            retry_delay_ms=proto.retry_delay_ms or 5000,
            next_run_at=next_run,
        )

    def calculate_next_run(self, from_time: datetime | None = None) -> datetime:
        """
        Calculate next run time based on cron expression.

        Args:
            from_time: Base time for calculation (default: now)

        Returns:
            Next run datetime in UTC
        """
        from croniter import croniter

        now = from_time or datetime.now(tz=zoneinfo.ZoneInfo("UTC"))

        # Convert to schedule timezone
        try:
            tz = zoneinfo.ZoneInfo(self.timezone)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")

        local_now = now.astimezone(tz)

        # Calculate next run
        try:
            cron = croniter(self.cron_expression, local_now)
            next_run = cron.get_next(datetime)
        except Exception:
            # Fallback: tomorrow at 9:00
            from datetime import timedelta

            next_run = local_now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
                days=1
            )

        # Return in UTC
        return next_run.astimezone(zoneinfo.ZoneInfo("UTC"))

    @property
    def timeout_seconds(self) -> int:
        """Timeout in seconds."""
        return self.timeout_ms // 1000

    @property
    def retry_delay_seconds(self) -> int:
        """Retry delay in seconds."""
        return self.retry_delay_ms // 1000

    @property
    def cron_description(self) -> str:
        """Human-readable cron description."""
        try:
            parts = self.cron_expression.split()
            if len(parts) != 5:
                return self.cron_expression

            minute, hour, day, month, weekday = parts

            # Common patterns
            if self.cron_expression == "* * * * *":
                return "Every minute"
            if minute != "*" and hour != "*" and day == "*" and month == "*" and weekday == "*":
                return f"Daily at {hour.zfill(2)}:{minute.zfill(2)}"
            if (
                minute != "*"
                and hour != "*"
                and day == "*"
                and month == "*"
                and weekday != "*"
            ):
                days = {
                    "0": "Sun",
                    "1": "Mon",
                    "2": "Tue",
                    "3": "Wed",
                    "4": "Thu",
                    "5": "Fri",
                    "6": "Sat",
                }
                day_name = days.get(weekday, weekday)
                return f"Every {day_name} at {hour.zfill(2)}:{minute.zfill(2)}"
            if minute.startswith("*/"):
                interval = minute[2:]
                return f"Every {interval} minutes"
            if hour.startswith("*/"):
                interval = hour[2:]
                return f"Every {interval} hours"

            return self.cron_expression
        except Exception:
            return self.cron_expression


class ScheduleResult(BaseModel):
    """Result of schedule execution."""

    schedule_id: str
    run_id: str
    status: ScheduleRunStatus
    result: dict[str, Any] | None = None
    error: str | None = None
    items_processed: int = 0
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "schedule_id": self.schedule_id,
            "run_id": self.run_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "items_processed": self.items_processed,
            "duration_ms": self.duration_ms,
        }


__all__ = ["Schedule", "ScheduleResult", "ScheduleRunStatus"]
