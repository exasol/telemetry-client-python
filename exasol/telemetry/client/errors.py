class TelemetryError(Exception):
    """
    Telemetry exception, thrown from telemetry client methods.
    """

    def __init__(self, message):
        super().__init__(message)
