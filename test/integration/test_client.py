import pytest

from exasol.telemetry.client import *
from exasol.telemetry.client import worker

ENDPOINT = ""


@pytest.mark.skip()
def test_client():
    assert setup(ENDPOINT, disable=False)
    try:
        assert worker.send_features({"test_feat": [1]})
    finally:
        shutdown(flush_buffers=True)
