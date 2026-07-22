import pytest

from exasol.telemetry.client import (
    TelemetryError,
    config,
)
from exasol.telemetry.client.setup import shutdown


@pytest.fixture
def telemetry_reset():
    """
    Call `shutdown()` after the test.
    """
    yield
    try:
        shutdown()
    except TelemetryError:
        pass


@pytest.fixture()
def telemetry_unset_ci(monkeypatch):
    """
    Temporary remove CI env variable if present
    """
    monkeypatch.delenv(config.ENV_CI, raising=False)
    yield
