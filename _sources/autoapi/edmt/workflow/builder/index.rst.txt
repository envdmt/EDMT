edmt.workflow.builder
=====================

.. py:module:: edmt.workflow.builder






Module Contents
---------------

.. py:data:: Frequency

.. py:data:: ReducerName

.. py:function:: ee_initialized(project: str | None = None) -> None

   Initialize Earth Engine only once.

   Notes:
   - Uses the public ee.data.is_initialized() instead of private ee.data._initialized.
   - Newer EE setups typically require a Cloud project for Initialize().


.. py:function:: gdf_to_ee_geometry(gdf: geopandas.GeoDataFrame) -> ee.Geometry

