"""
Constants for gRPC stream service.

Centralized configuration values for keepalive, timeouts, and queue limits.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════
# KEEPALIVE SETTINGS
# ═══════════════════════════════════════════════════════════

# CMDOP Go uses 10s, we match for faster detection
KEEPALIVE_TIME_MS = 10000  # Send PING every 10s (was 30s)
KEEPALIVE_TIMEOUT_MS = 5000  # Wait 5s for PING response (was 10s)

# ═══════════════════════════════════════════════════════════
# TIMEOUT SETTINGS
# ═══════════════════════════════════════════════════════════

SEND_TIMEOUT = 10.0  # seconds - timeout for send operations
RECEIVE_TIMEOUT = 45.0  # seconds - timeout for receive operations

# ═══════════════════════════════════════════════════════════
# HEARTBEAT FAILURE DETECTION
# ═══════════════════════════════════════════════════════════

MAX_HEARTBEAT_FAILURES = 3  # Disconnect after N consecutive failures

# ═══════════════════════════════════════════════════════════
# SILENCE DETECTION
# ═══════════════════════════════════════════════════════════

SILENCE_TIMEOUT = 120.0  # 2 minutes without any message

# ═══════════════════════════════════════════════════════════
# QUEUE LIMITS
# ═══════════════════════════════════════════════════════════

OUTGOING_QUEUE_MAX_SIZE = 1000  # Prevent unbounded memory growth

# ═══════════════════════════════════════════════════════════
# CONNECTION STATE MONITORING
# ═══════════════════════════════════════════════════════════

CONNECTION_STATE_CHECK_INTERVAL = 5.0  # Check state every 5 seconds


__all__ = [
    "KEEPALIVE_TIME_MS",
    "KEEPALIVE_TIMEOUT_MS",
    "SEND_TIMEOUT",
    "RECEIVE_TIMEOUT",
    "MAX_HEARTBEAT_FAILURES",
    "SILENCE_TIMEOUT",
    "OUTGOING_QUEUE_MAX_SIZE",
    "CONNECTION_STATE_CHECK_INTERVAL",
]
