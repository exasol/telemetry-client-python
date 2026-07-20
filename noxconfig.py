from pathlib import Path

from exasol.toolbox.config import BaseConfig


class Config(BaseConfig):
    pass


PROJECT_CONFIG = Config(
    project_name="telemetry",
    root_path=Path(__file__).parent,
    python_versions=("3.13",),
    exasol_versions=("8.29.13",),
)
