import pytest

from exasol.telemetry.client import *


@pytest.mark.skip()
def test_client():
    try:
        track("test", "0.1", "test-feature")
    finally:
        shutdown(flush_buffers=True)
