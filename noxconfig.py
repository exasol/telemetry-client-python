from pathlib import Path

from exasol.toolbox.config import BaseConfig


class Config(BaseConfig):
    pass


PROJECT_CONFIG = Config(
    # this is "telemetry" and not "telemetry-client-python" to have the package exasol.telemetry.client,
    # not exasol.telemetry-client-python
    project_name="telemetry",
    root_path=Path(__file__).parent,
    python_versions=("3.13",),
    exasol_versions=("8.29.13",),
)
