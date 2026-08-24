"""
Telemetry client library for python.

Public API is three methods:
- track: remembers the feature name in the buffer (will be sent in background)
- disable: disables the telemetry
- shutdown: cleans up the resources and sends the data still in buffers
"""

from exasol.telemetry.client.config import disable
from exasol.telemetry.client.setup import shutdown
from exasol.telemetry.client.worker import track

__all__ = ["track", "disable", "shutdown"]
