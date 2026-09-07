import typing as tt
import logging

LOGGER = "exasol.telemetry.client"
LEVEL = logging.DEBUG

logger: tt.Optional[logging.Logger] = None


def setup_logging():
    """
    Enable logging for our package.
    """
    global logger
    # prevent double-initialization
    if logger is not None:
        return
    logger = logging.getLogger(LOGGER)
    logger.setLevel(LEVEL)


def log(msg: str, *args, **kwargs):
    global logger
    if logger is not None:
        logger.log(LEVEL, msg, *args, **kwargs)
