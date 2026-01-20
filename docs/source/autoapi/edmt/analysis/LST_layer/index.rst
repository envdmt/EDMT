edmt.analysis.LST_layer
=======================

.. py:module:: edmt.analysis.LST_layer




Module Contents
---------------

.. py:function:: get_lst_image(start_date: str, end_date: str, satellite: str = 'MODIS', roi_gdf: Optional[geopandas.GeoDataFrame] = None, reducer: Literal['mean', 'median', 'min', 'max'] = 'mean') -> ee.Image

   Generate a single composite Earth Engine image of Land Surface Temperature (LST) in degrees Celsius 
   for visualization or mapping purposes.

   The function retrieves LST data from a specified satellite sensor over a given date range, 
   converts raw values to Celsius, applies a temporal reducer (e.g., mean, median), and optionally 
   clips the result to a region of interest.

   Parameters
   ----------
   start_date : str
       Start date of the time window in 'YYYY-MM-DD' format.
   end_date : str
       End date of the time window in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame (Polygon/MultiPolygon). If provided, will be
       converted internally using gdf_to_ee_geometry() and used for filterBounds + clip.
   reducer : {"mean", "median", "min", "max"}, optional
       Temporal aggregation method to combine images across the time period (default: "mean").

   Returns
   -------
   ee.Image
       A single-band Earth Engine image with band name "LST_C", containing LST values in °C. 
       Suitable for display with `Map.addLayer(...)` in Earth Engine environments.

   Raises
   ------
   ValueError
       If an unsupported reducer is provided.



.. py:function:: get_lst_collection(start_date: str, end_date: str, satellite: str = 'MODIS', frequency: Literal['weekly', 'monthly', 'yearly'] = 'monthly', roi_gdf: Optional[geopandas.GeoDataFrame] = None) -> ee.ImageCollection

   Generate an Earth Engine ImageCollection of Land Surface Temperature (LST) composites 
   aggregated over regular time periods (weekly, monthly, or yearly), in degrees Celsius.

   Each image in the collection represents the mean LST over one period, includes metadata 
   about the period start, and is optionally clipped to a region of interest.

   Parameters
   ----------
   start_date : str
       Start date of the overall time window in 'YYYY-MM-DD' format.
   end_date : str
       End date of the overall time window in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
   frequency : {"weekly", "monthly", "yearly"}, optional
       Temporal aggregation interval for compositing (default: "monthly").
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame (Polygon/MultiPolygon). If provided, will be
       converted internally using gdf_to_ee_geometry() and used for filterBounds + clip.


   Returns
   -------
   ee.ImageCollection
       An ImageCollection where each image:
       - Contains one band named `"LST_C"` with LST values in °C.
       - Has the property `"system:time_start"` set to the period start (in milliseconds since Unix epoch).
       - Includes additional properties: `"period_start"` (formatted as "YYYY-MM-dd") and `"satellite"`.

   Raises
   ------
   ValueError
       If `frequency` is not one of the supported options.



