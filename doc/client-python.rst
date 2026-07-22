Python Client library
=====================

Installation
------------

(this way is not working at the moment, as package wasn’t deployed to
public repo yet) ``pip install exasol-telemetry-client``

Usage
-----

Once installed, package ``exasel.telemetry.client`` provides three
methods and one exception: - ``setup()``: configures the library, has to
be called once in the beginning - ``track(feature_name)``: tracks
feature as used (string) - ``shutdown()``: should be called at the end
of the program. If not called, some tracked features could be lost. -
``TelemetryError``: exception could be thrown during ``setup()`` call,
if environment variables are wrong.

Function ``was_setup()`` could be used to check the ``setup()`` was called
before (possibly in another library).

Example of minimalistic program:

.. code:: python

   import logging
   from exasol.telemetry.client import *

   if __name__ == "__main__":
       try:
           try:
               if not was_setup():
                   setup()
           except TelemetryError as e:
               logging.warning("Telemetry disabled due to error: %s", str(e))

           track("feature1")
           track("feature2")
       finally:
           shutdown()

Exceptions
----------

Exception ``TelemetryError`` could be thrown from ``setup()`` and
``shutdown()`` in case of errors. Call of ``track()`` never raises exceptions, in case of errors
tracked feature is ignored.

Environment variables
---------------------

To change the telemetry configuration, you can set the following
environment variables. Those values also could be changed via
``setup()`` arguments.

-  ``EXASOL_TELEMETRY_DISABLE`` - any value disables the telemetry data
   collection and sending
-  ``EXASOL_TELEMETRY_ENDPOINT`` - redefines telemetry endpoint url.

In addition, if environment variable ``CI=true`` (which is the case during Github CI workflows run)
the telemetry is disabled unless explicitly enabled with ``setup()`` arguments.
