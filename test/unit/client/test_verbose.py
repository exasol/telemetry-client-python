from exasol.telemetry.client import verbose
import logging


def test_no_show_unconfigured(caplog, telemetry_reset):
    logging.log(verbose.LEVEL, "Test")
    assert "Test" not in caplog.text
    caplog.clear()

    verbose.log("Test")
    assert "Test" not in caplog.text


def test_show_configured(caplog, telemetry_reset):
    verbose.setup_logging()
    verbose.log("Test")
    assert "Test" in caplog.text

    # second setup changes nothing
    verbose.setup_logging()
    caplog.clear()
    verbose.log("Test2")
    assert "Test2" in caplog.text
