"""Service state machine for managing service lifecycle states."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ServiceState(str, Enum):
    """
    Service lifecycle states.

    State transitions:
        INITIALIZED -> REGISTERING -> RUNNING
        RUNNING -> PAUSED -> RUNNING
        RUNNING -> STOPPING -> STOPPED
        RUNNING -> ERROR -> STOPPING -> STOPPED
        * -> ERROR (from any state on error)
    """

    INITIALIZED = "initialized"
    REGISTERING = "registering"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


# Valid state transitions map
_VALID_TRANSITIONS: dict[ServiceState, set[ServiceState]] = {
    ServiceState.INITIALIZED: {ServiceState.REGISTERING, ServiceState.ERROR},
    ServiceState.REGISTERING: {ServiceState.RUNNING, ServiceState.ERROR},
    ServiceState.RUNNING: {
        ServiceState.PAUSED,
        ServiceState.STOPPING,
        ServiceState.ERROR,
    },
    ServiceState.PAUSED: {
        ServiceState.RUNNING,
        ServiceState.STOPPING,
        ServiceState.ERROR,
    },
    ServiceState.STOPPING: {ServiceState.STOPPED, ServiceState.ERROR},
    ServiceState.STOPPED: set(),
    ServiceState.ERROR: {ServiceState.STOPPING, ServiceState.STOPPED},
}


class StateTransitionError(Exception):
    """Invalid state transition attempted."""

    def __init__(
        self,
        from_state: ServiceState,
        to_state: ServiceState,
        message: str | None = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        default_msg = f"Cannot transition from {from_state.value} to {to_state.value}"
        super().__init__(message or default_msg)


def can_transition(from_state: ServiceState, to_state: ServiceState) -> bool:
    """Check if state transition is valid."""
    valid_targets = _VALID_TRANSITIONS.get(from_state, set())
    return to_state in valid_targets


def validate_transition(from_state: ServiceState, to_state: ServiceState) -> None:
    """Validate state transition, raise if invalid."""
    if not can_transition(from_state, to_state):
        raise StateTransitionError(from_state, to_state)


class StateSnapshot(BaseModel):
    """Immutable snapshot of state machine state."""

    model_config = ConfigDict(frozen=True)

    current: ServiceState = Field(description="Current state")
    history: tuple[ServiceState, ...] = Field(
        default_factory=tuple,
        description="State history",
    )


class StateMachine(BaseModel):
    """
    State machine for tracking service state.

    Example:
        ```python
        sm = StateMachine()
        assert sm.state == ServiceState.INITIALIZED

        sm.transition_to(ServiceState.REGISTERING)
        sm.transition_to(ServiceState.RUNNING)

        # Invalid transition raises
        sm.transition_to(ServiceState.INITIALIZED)  # StateTransitionError
        ```
    """

    model_config = ConfigDict(validate_assignment=True)

    state: ServiceState = Field(
        default=ServiceState.INITIALIZED,
        description="Current state",
    )
    history: list[ServiceState] = Field(
        default_factory=lambda: [ServiceState.INITIALIZED],
        description="State transition history",
    )

    def can_transition_to(self, target: ServiceState) -> bool:
        """Check if transition to target state is valid."""
        return can_transition(self.state, target)

    def transition_to(self, target: ServiceState) -> ServiceState:
        """
        Transition to new state.

        Args:
            target: Target state

        Returns:
            New state

        Raises:
            StateTransitionError: If transition is invalid
        """
        validate_transition(self.state, target)
        self.state = target
        self.history.append(target)
        return self.state

    def is_running(self) -> bool:
        """Check if service is in running state."""
        return self.state == ServiceState.RUNNING

    def is_active(self) -> bool:
        """Check if service is active (running or paused)."""
        return self.state in (ServiceState.RUNNING, ServiceState.PAUSED)

    def is_terminal(self) -> bool:
        """Check if service is in terminal state."""
        return self.state in (ServiceState.STOPPED, ServiceState.ERROR)

    def get_snapshot(self) -> StateSnapshot:
        """Get immutable snapshot of current state."""
        return StateSnapshot(
            current=self.state,
            history=tuple(self.history),
        )


__all__ = [
    "ServiceState",
    "StateTransitionError",
    "StateSnapshot",
    "StateMachine",
    "can_transition",
    "validate_transition",
]
