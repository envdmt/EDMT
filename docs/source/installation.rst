Installation
============

EDMT can be installed with the core dependencies or with optional extras,
depending on the functionality you need.

Core Installation
-----------------

Install the core EDMT package:

.. code-block:: console

   pip install edmt

This installs all required dependencies for geospatial analysis, Google Earth
Engine integration, remote sensing, and data processing.

Optional DuckDB Support
-----------------------

Some EDMT features support high-performance data storage and querying using
DuckDB. To enable these features, install EDMT with the ``duckdb`` extra:

.. code-block:: console

   pip install "edmt[duckdb]"

Or install all optional dependencies:

.. code-block:: console

   pip install "edmt[all]"

Verify the Installation
-----------------------

After installation, verify that EDMT is installed correctly:

.. code-block:: python

   import edmt

   edmt.init()

If no errors are raised, EDMT has been installed successfully.

Notes
-----

- ``pip install edmt`` installs the core package only.
- DuckDB is an optional dependency and is only required for features that
  use DuckDB for data storage or analytics.
- If you attempt to use a DuckDB feature without installing the optional
  dependency, EDMT will prompt you to install it using:

  .. code-block:: console

     pip install "edmt[duckdb]"
