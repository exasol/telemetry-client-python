import pytest

from exasol.telemetry.client import config
from exasol.telemetry.client.setup import shutdown


@pytest.fixture
def telemetry_reset():
    """
    Resets the telemetry into initial state
    """
    yield
    shutdown()
    config.store(None)


@pytest.fixture
def telemetry_unset_ci(monkeypatch):
    """
    Temporary remove CI env variable if present
    """
    monkeypatch.delenv(config.ENV_CI, raising=False)


@pytest.fixture
def telemetry_unset_disable(monkeypatch):
    """
    Temporary remove EXASOL_TELEMETRY_DISABLE env variable if present
    """
    monkeypatch.delenv(config.ENV_DISABLE, raising=False)
