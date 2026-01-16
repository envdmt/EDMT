edmt.analysis.analysis
======================

.. py:module:: edmt.analysis.analysis




Module Contents
---------------

.. py:function:: initialize_gee()

   Initialize Google Earth Engine with explicit project support.


.. py:function:: geodf_to_ee_geometry(gdf: geopandas.GeoDataFrame) -> ee.Geometry

   Convert a GeoDataFrame polygon/multipolygon to ee.Geometry.

   Parameters
   ----------
   gdf : geopandas.GeoDataFrame
       Must contain Polygon or MultiPolygon geometries

   Returns
   -------
   ee.Geometry


