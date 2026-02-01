"""
Circuit Breaker pattern for gRPC connection management.

Implements three-state machine (CLOSED → OPEN → HALF_OPEN) to prevent
cascading failures and allow graceful recovery.

Based on CMDOP Go implementation patterns.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation - requests allowed
    OPEN = "open"  # Blocking requests - fail fast
    HALF_OPEN = "half_open"  # Testing recovery - limited requests


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    failure_threshold: Annotated[int, Field(ge=1, le=20)] = 5
    """Number of consecutive failures before opening circuit."""

    success_threshold: Annotated[int, Field(ge=1, le=10)] = 2
    """Number of consecutive successes in half-open to close circuit."""

    recovery_timeout: Annotated[float, Field(gt=0, le=300)] = 60.0
    """Seconds to wait before transitioning from OPEN to HALF_OPEN."""

    half_open_max_calls: Annotated[int, Field(ge=1, le=10)] = 3
    """Maximum concurrent test calls in HALF_OPEN state."""


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    successes: int = 0
    total_failures: int = 0
    total_successes: int = 0
    last_failure_at: datetime | None = None
    last_success_at: datetime | None = None
    opened_at: datetime | None = None
    state_changes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for gRPC connection resilience.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit tripped, requests fail fast
    - HALF_OPEN: Testing if service recovered

    Transitions:
    - CLOSED → OPEN: After N consecutive failures
    - OPEN → HALF_OPEN: After recovery timeout
    - HALF_OPEN → CLOSED: After M consecutive successes
    - HALF_OPEN → OPEN: On any failure
    """

    __slots__ = (
        "_config",
        "_state",
        "_failures",
        "_successes",
        "_total_failures",
        "_total_successes",
        "_opened_at",
        "_last_failure_at",
        "_last_success_at",
        "_half_open_calls",
        "_state_changes",
        "_lock",
    )

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self._config = config or CircuitBreakerConfig()
        self._state: CircuitState = CircuitState.CLOSED
        self._failures: int = 0
        self._successes: int = 0
        self._total_failures: int = 0
        self._total_successes: int = 0
        self._opened_at: datetime | None = None
        self._last_failure_at: datetime | None = None
        self._last_success_at: datetime | None = None
        self._half_open_calls: int = 0
        self._state_changes: int = 0
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    @property
    def recovery_timeout(self) -> float:
        """Get recovery timeout in seconds."""
        return self._config.recovery_timeout

    def allow_request(self) -> bool:
        """
        Check if a request should be allowed.

        Returns:
            True if request should proceed, False if circuit is open
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if self._opened_at:
                    elapsed = (datetime.now(timezone.utc) - self._opened_at).total_seconds()
                    if elapsed >= self._config.recovery_timeout:
                        self._transition_to(CircuitState.HALF_OPEN)
                        self._successes = 0
                        self._half_open_calls = 1  # Count this call as the first test call
                        return True
                return False

            # HALF_OPEN: Allow limited test calls
            if self._half_open_calls < self._config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def record_success(self) -> None:
        """Record a successful operation."""
        with self._lock:
            self._failures = 0
            self._total_successes += 1
            self._last_success_at = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                self._successes += 1
                if self._successes >= self._config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    logger.info("Circuit breaker closed after %d successes", self._successes)

    def record_failure(self) -> None:
        """Record a failed operation."""
        with self._lock:
            self._failures += 1
            self._total_failures += 1
            self._last_failure_at = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._transition_to(CircuitState.OPEN)
                self._opened_at = datetime.now(timezone.utc)
                logger.warning("Circuit breaker reopened on failure during half-open")
            elif self._state == CircuitState.CLOSED:
                if self._failures >= self._config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
                    self._opened_at = datetime.now(timezone.utc)
                    logger.warning(
                        "Circuit breaker opened after %d consecutive failures",
                        self._failures,
                    )

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state (must hold lock)."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._state_changes += 1
            logger.debug(
                "Circuit breaker state: %s → %s (transition #%d)",
                old_state.value,
                new_state.value,
                self._state_changes,
            )

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._successes = 0
            self._opened_at = None
            self._half_open_calls = 0
            logger.info("Circuit breaker reset")

    def get_stats(self) -> CircuitBreakerStats:
        """Get current statistics."""
        with self._lock:
            return CircuitBreakerStats(
                state=self._state,
                failures=self._failures,
                successes=self._successes,
                total_failures=self._total_failures,
                total_successes=self._total_successes,
                last_failure_at=self._last_failure_at,
                last_success_at=self._last_success_at,
                opened_at=self._opened_at,
                state_changes=self._state_changes,
            )


class BackoffStrategy:
    """
    Exponential backoff with jitter for reconnection.

    Supports two phases:
    - Fast phase: Rapid retries for transient failures
    - Slow phase: Standard exponential backoff
    """

    __slots__ = (
        "_initial_delay",
        "_max_delay",
        "_multiplier",
        "_jitter",
        "_fast_delay",
        "_fast_attempts",
        "_attempt",
    )

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 120.0,
        multiplier: float = 1.6,
        jitter: float = 0.1,
        fast_delay: float = 0.1,
        fast_attempts: int = 0,
    ) -> None:
        """
        Initialize backoff strategy.

        Args:
            initial_delay: Initial delay in seconds for slow phase
            max_delay: Maximum delay in seconds
            multiplier: Delay multiplier for exponential growth
            jitter: Jitter factor (0.1 = ±10% randomness)
            fast_delay: Delay for fast phase attempts
            fast_attempts: Number of fast phase attempts before slow phase
        """
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._multiplier = multiplier
        self._jitter = jitter
        self._fast_delay = fast_delay
        self._fast_attempts = fast_attempts
        self._attempt = 0

    def next(self) -> float:
        """
        Get next delay with jitter.

        Returns:
            Delay in seconds
        """
        self._attempt += 1

        # Fast phase: rapid retries
        if self._attempt <= self._fast_attempts:
            delay = self._fast_delay
        else:
            # Slow phase: exponential backoff
            slow_attempt = self._attempt - self._fast_attempts
            delay = self._initial_delay * (self._multiplier ** (slow_attempt - 1))
            delay = min(delay, self._max_delay)

        # Apply jitter (±jitter%)
        jitter_range = delay * self._jitter
        delay += random.uniform(-jitter_range, jitter_range)

        return max(delay, 0.01)  # Ensure positive

    def reset(self) -> None:
        """Reset attempt counter."""
        self._attempt = 0

    @property
    def attempt(self) -> int:
        """Get current attempt number."""
        return self._attempt

    @classmethod
    def standard(cls) -> BackoffStrategy:
        """Create standard backoff strategy (1s → 120s, 1.6x, ±10% jitter)."""
        return cls(
            initial_delay=1.0,
            max_delay=120.0,
            multiplier=1.6,
            jitter=0.1,
        )

    @classmethod
    def aggressive(cls) -> BackoffStrategy:
        """
        Create aggressive backoff strategy for transient failures.

        Fast phase: 30 attempts at 100ms each (3 seconds total)
        Slow phase: 500ms → 10s, 1.5x, ±10% jitter
        """
        return cls(
            initial_delay=0.5,
            max_delay=10.0,
            multiplier=1.5,
            jitter=0.1,
            fast_delay=0.1,
            fast_attempts=30,
        )

    @classmethod
    def conservative(cls) -> BackoffStrategy:
        """Create conservative backoff strategy (2s → 300s, 2x, ±10% jitter)."""
        return cls(
            initial_delay=2.0,
            max_delay=300.0,
            multiplier=2.0,
            jitter=0.1,
        )


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerStats",
    "CircuitState",
    "BackoffStrategy",
]
