import dataclasses
import typing as tt

# === Environment variables to control the telemetry
# Any value will disable telemetry communication entirely
ENV_DISABLE = "EXASOL_TELEMETRY_DISABLE"
# Endpoint (has to be valid http/https URL)
ENV_ENDPOINT = "EXASOL_TELEMETRY_ENDPOINT"
# GitHub CI sets this to true during execution
ENV_CI = "CI"

# === Default values if no env or setup() arguments were provided
DEFAULT_DISABLED = False
DEFAULT_ENDPOINT = "https://metrics.exasol.com/telemetry"


@dataclasses.dataclass(frozen=True)
class Config:
    enabled: bool
    endpoint: str


# Indication of Telemetry library initialization
_config: tt.Optional[Config] = None


def get() -> tt.Optional[Config]:
    global _config
    return _config


def store(config: tt.Optional[Config]):
    global _config
    _config = config


def was_setup() -> bool:
    """
    Returns the status of setup().

    :return: True if setup() was called successfully, False otherwise
    """
    return get() is not None


def was_enabled() -> bool:
    """
    Returns True if telemetry was setup and enabled.
    """
    conf = get()
    return conf is not None and conf.enabled
