import pytest

from exasol.telemetry.client import config
from exasol.telemetry.client.config import was_setup
from exasol.telemetry.client.setup import (
    get_value,
    is_valid_endpoint_url,
    setup,
    shutdown,
)


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://something.com", True),
        ("https://google.com/search", True),
        ("ftp://google.com/test", False),
        ("not-an-url", False),
    ],
)
def test_is_valid_endpoint_url(url, expected):
    assert is_valid_endpoint_url(url) == expected


def test_get_value_explicit(monkeypatch):
    monkeypatch.setenv("TEST_ENV", "val1")
    # explicit value has a priority
    r = get_value("val_exp", "TEST_ENV", "val_def")
    assert r == "val_exp"


def test_get_value_env(monkeypatch):
    monkeypatch.setenv("TEST_ENV", "val1")
    # no explicit -> env is used
    r = get_value(None, "TEST_ENV", "val_def")
    assert r == "val1"


def test_get_value_default(monkeypatch):
    monkeypatch.setenv("TEST_ENV", "val1")
    # last resort - default value
    r = get_value(None, "UNK_ENV", "val_def")
    assert r == "val_def"


def test_setup_explicit_enabled(telemetry_reset):
    assert not config.was_setup()

    assert setup("http://endpoint", disable=False)
    assert config.was_setup()
    assert config.was_enabled()


def test_setup_explicit_disabled(telemetry_reset):
    assert not config.was_setup()

    assert not setup("https://endpoint", disable=True)
    assert config.was_setup()
    assert not config.was_enabled()
    assert config.get().endpoint.startswith("https")


def test_setup_wrong_endpoint(
    telemetry_reset, telemetry_unset_ci, telemetry_unset_disable
):
    assert not setup("ftp://test.com")
    assert config.was_setup()
    assert not config.was_enabled()


def test_setup_env_disabled(
    monkeypatch, telemetry_reset, telemetry_unset_ci, telemetry_unset_disable
):
    monkeypatch.setenv(config.ENV_DISABLE, "1")
    assert not setup("http://endpoint")
    assert config.was_setup()
    assert not config.was_enabled()
    # double-call to setup skips reconfiguration and returns the enable status
    assert not setup(disable=False)


def test_setup_env_enabled(
    monkeypatch, telemetry_reset, telemetry_unset_ci, telemetry_unset_disable
):
    monkeypatch.setenv(config.ENV_ENDPOINT, "http://test")
    assert setup()
    assert config.was_enabled()
    assert config.get().endpoint == "http://test"


def test_setup_defaults(telemetry_reset, telemetry_unset_ci, telemetry_unset_disable):
    assert setup() == (not config.DEFAULT_DISABLED)
    assert config.get().endpoint == config.DEFAULT_ENDPOINT


def test_setup_ci_true(monkeypatch, telemetry_reset):
    monkeypatch.setenv(config.ENV_CI, "true")
    assert not setup()
    assert not config.was_enabled()


def test_setup_ci_true_explicit(monkeypatch, telemetry_reset, telemetry_unset_disable):
    monkeypatch.setenv(config.ENV_CI, "true")
    assert setup(disable=False)


def test_setup_ci_false(monkeypatch, telemetry_reset, telemetry_unset_disable):
    monkeypatch.setenv(config.ENV_CI, "t")
    assert setup()


def test_shutdown_not_setup(telemetry_reset):
    shutdown()
    assert not was_setup()
