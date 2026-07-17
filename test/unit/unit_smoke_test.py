import exasol.telemetry  # noqa: F401 - This import is needed for a smoke test.
from exasol.telemetry import __version__


def test_unit_smoke_test():
    assert isinstance(__version__, str)
