import os
import typing as tt
from urllib.parse import urlparse

from exasol.telemetry.client import (
    config,
    worker,
)


def get_value(
    val_explicit: tt.Optional[tt.Any],
    env_variable: str,
    val_default: tt.Any,
    env_convertor: tt.Callable[[str], tt.Any] = str,
) -> tt.Any:
    """
    Configuration value accessor. If explicit value is given, return it, then tries to
    obtain value from environment. If environment value is not set, returns default.
    :param val_explicit: explicit value (optional)
    :param env_variable: environment variable name
    :param val_default: default value to return on last resort
    :param env_convertor: function to convert environment variable into value
    :return: value
    """
    if val_explicit is not None:
        return val_explicit
    if env_variable not in os.environ:
        return val_default
    env_val = os.environ[env_variable]
    return env_convertor(env_val)


def is_valid_endpoint_url(url: str) -> bool:
    """
    Checks that given string is a valid url.
    :param url: url to check
    :return: True if valid
    """
    res = urlparse(url)
    return res.scheme in ("http", "https") and len(res.netloc) > 0


def setup(endpoint: tt.Optional[str] = None, disable: tt.Optional[bool] = None) -> bool:
    """
    Telemetry client setup function.

    Explicitly given arguments have the highest priority.
    If they are not given, we check the environment variables (EXASOL_TELEMETRY_XXX),
    if no environment value, we use defaults (DEFAULT_XXX).

    If setup() was called before, we return the enabled status and do not reconfigure.

    :param endpoint: Telemetry endpoint to send data. If not given,
    default endpoint is used.
    :param disable: If True, disable telemetry communication and
    data accumulation.

    :returns True if telemetry is active according to configuration,
    False if it was disabled
    """
    if config.was_setup():
        return config.was_enabled()
    val_endpoint = get_value(endpoint, config.ENV_ENDPOINT, config.DEFAULT_ENDPOINT)

    # Checking the presence of CI=true env variable
    val_disabled = get_value(
        disable,
        config.ENV_CI,
        config.DEFAULT_DISABLED,
        env_convertor=lambda v: v == "true",
    )

    # As any value given in ENV_DISABLE env var should disable telemetry,
    # env_convertor returns True
    val_disabled = get_value(
        disable,
        config.ENV_DISABLE,
        val_disabled,
        env_convertor=lambda _: True,
    )
    enabled = not val_disabled

    if enabled and not is_valid_endpoint_url(val_endpoint):
        enabled = False

    conf = config.Config(endpoint=val_endpoint, enabled=enabled)
    config.store(conf)
    worker.start_worker()
    return conf.enabled


def shutdown(flush_buffers: bool = True):
    """
    Perform library clean-up (trying to send the dry buffers).
    :param flush_buffers: If True (default), we'll try to send the
    buffers, which might introduce delay. If set to False, no data is sent,
    so some values might be lost.
    """
    if not config.was_setup():
        return
    worker.stop_worker(flush_buffers)
    config.disable()
