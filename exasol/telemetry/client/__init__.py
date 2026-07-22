"""
Telemetry client library for python.

Public API is three methods:
- setup: initializes the library based on explicit arguments or environment variables
- shutdown: cleans up the resources and sends the data still in buffers
- track: remembers the feature name in the buffer (will be sent in background)

On error we raise exception TelemetryError with error message.
"""

from exasol.telemetry.client.config import was_setup
from exasol.telemetry.client.errors import TelemetryError
from exasol.telemetry.client.setup import (
    setup,
    shutdown,
)
from exasol.telemetry.client.worker import track

__all__ = ["was_setup", "setup", "shutdown", "track", "TelemetryError"]
