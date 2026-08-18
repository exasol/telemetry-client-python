Telemetry Protocol Specification
================================

Exasol telemetry uses simplistic protocol sending events happened in the the software.
Every event has a timestamp attached to be used for server-side analytics.
All the data one the server are immediately aggregated and anonymized and no personal information
is transferred or stored.

The data is transferred in json format and at the moment there are two versions of the protocol.

Version 0.1
-----------
.. code:: json

    {
        "version": "0.1",
        "timestamp": 1787036195,
        "features": {
            "mcp-server.started": [1787036195]
        }
    }

Transferred data has the following fields:

-  ``version``: string specifying the protocol version
-  ``timestamp``: UTC timestamp of the transmission attempt
-  ``features``: dictionary with pairs ``feature-name`` and vector of timestamps when the event happened.

Recording of both event timestamp and transmission timestamp allows to check the clock discrepancies on the client
side and filter out outliers.

Version 0.2
-----------

This is an extension of version 0.1, sample data is below.
.. code:: json

    {
        "version": "0.2",
        "category": "mcp-server",
        "productVersion": "0.22",
        "timestamp": 1787036195,
        "features": {
            "started": [1787036195]
        }
    }

In this version we have two new top-level fields added:

-  ``category``: name of the product
-  ``productVersion``: version of the product

The name of the product is no longer prepended to the features, which makes the data more compact.