Python Client library
=====================

Installation
------------

(this way is not working at the moment, as package wasn’t deployed to
public repo yet) ``pip install exasol-telemetry-client``

Usage
-----

Once installed, package ``exasel.telemetry.client`` provides three
methods:

- ``track(product_name, product_version, feature_name)``: tracks feature as used (string)
- ``shutdown()``: should be called at the end of the program. If not called, some tracked features could be lost.
- ``disable()``: disables telemetry entirely for the whole process till the termination of the process. It is useful for cases when some software wants to disable telemetry even when some of its libraries are using it.

Explicit initialization of the library is not needed --- it will be set up on the first ``track()`` call.

Example of minimalistic program:

.. code:: python

   from exasol.telemetry.client import *

   if __name__ == "__main__":
       try:
           track("hello-world", "0.1", "started")
           core_of_the_program()
       finally:
           shutdown()

Environment variables
---------------------

To change the telemetry configuration, you can set the following
environment variables. Those values also could be changed via
``setup()`` arguments.

-  ``EXASOL_TELEMETRY_DISABLE`` - any value disables the telemetry data
   collection and sending
-  ``EXASOL_TELEMETRY_ENDPOINT`` - redefines telemetry endpoint url.
-  ``EXASOL_TELEMETRY_VERBOSE`` -- enables logging messages from the library. Could be used to make sure integration was done properly.

In addition, if environment variable ``CI=true`` (which is the case during Github CI workflows run).
