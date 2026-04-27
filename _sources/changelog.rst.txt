Changelog
=========

New Changes
----------------

Workflow structure has been improved to better support analysis requests and enhance visual outputs.

Breaking Changes
----------------

The following functions were removed:

- airPoint()
- airLine()
- airSegment()

Replacement
-----------

Use the unified API:

::

    get_flight_routes()

This new function generates flight routes from flight data.