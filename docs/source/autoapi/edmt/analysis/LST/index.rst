edmt.analysis.LST
=================

.. py:module:: edmt.analysis.LST




Module Contents
---------------

.. py:function:: get_lst_collection(satellite: str, start_date: str, end_date: str) -> tuple[ee.ImageCollection, dict]

   Retrieve a Land Surface Temperature (LST) ImageCollection and associated scaling parameters 
   from a specified satellite sensor.

   The function returns raw LST data (in digital numbers) along with metadata needed to convert 
   values to physical units (Kelvin). MODIS includes both day and night bands; other sensors 
   return a single thermal band.

   Parameters
   ----------
   satellite : str
       Satellite identifier. Supported options:
       - "MODIS": MOD11A1 (Terra) daily LST (day and night)
       - "LANDSAT8", "LANDSAT_8", or "LC08": Landsat 8 Collection 2 Level 2
       - "LANDSAT9", "LANDSAT_9", or "LC09": Landsat 9 Collection 2 Level 2
       - "GCOM": JAXA GCOM-C L3 LST product
   start_date : str
       Start date in 'YYYY-MM-DD' format.
   end_date : str
       End date in 'YYYY-MM-DD' format.

   Returns
   -------
   tuple[ee.ImageCollection, dict]
       - **ImageCollection**: Filtered to the date range and pre-selected thermal band(s):
           - MODIS: bands ["LST_Day_1km", "LST_Night_1km"]
           - Landsat 8/9: band ["ST_B10"]
           - GCOM: band ["LST_AVE"]
       - **factors**: Dictionary with scaling parameters for conversion to Kelvin:
           - `"multiply"`: Multiplicative factor
           - `"add"`: Additive offset
           - `"band"`: Default band name for primary LST (typically daytime)

   Raises
   ------
   ValueError
       If the satellite name is not supported.

   Notes
   -----
   Scaling equations:
     - MODIS (MOD11A1): LST [K] = DN × 0.02
     - Landsat 8/9 (C2 L2): LST [K] = DN × 0.00341802 + 149.0
     - GCOM-C: LST [K] = DN × 0.02


.. py:function:: compute_period_feature(start: ee.Date, collection: ee.ImageCollection, geometry: ee.Geometry, frequency: str, satellite: str, scale: Optional[int] = None) -> ee.Feature

   Compute spatial summary statistics (mean, median, min, max) for a specific LST band over a time period 
   and return them as an Earth Engine Feature with standardized property names.

   This function aggregates LST imagery over a temporal window (weekly, monthly, or yearly), computes 
   multiple spatial statistics over a region of interest, and renames output properties to generic 
   statistic names (e.g., "mean", "median") for consistency across satellites.

   Parameters
   ----------
   start : ee.Date
       Start date of the aggregation period.
   collection : ee.ImageCollection
       An LST ImageCollection containing the appropriate thermal band(s).
   geometry : ee.Geometry
       Region of interest over which to compute spatial statistics.
   frequency : {"weekly", "monthly", "yearly"}
       Temporal interval defining the period length.
   satellite : str
       Satellite name used to determine the default spatial resolution and primary LST band. 
       Supported: "MODIS", "LANDSAT8", "LANDSAT9", "GCOM".
   scale : int, optional
       Spatial resolution (in meters) for the reduction. If omitted, a sensor-specific default is used:
       - MODIS: 1000 m
       - Landsat 8/9: 30 m (300 for easier cloud compute for Large ROI)
       - GCOM: 4638 m

   Returns
   -------
   ee.Feature
       A feature with no geometry and the following properties:
       - "date": Period start formatted as "YYYY-MM-dd"
       - "satellite": Uppercase satellite name
       - "band": Name of the LST band used (e.g., "LST_Day_1km")
       - "mean", "median", "min", "max": Computed LST statistics in Kelvin (or Celsius if pre-converted)

   Raises
   ------
   ValueError
       If `satellite` is not supported or lacks a defined default scale.


.. py:function:: compute_lst_timeseries(start_date: str, end_date: str, satellite: str = 'MODIS', frequency: str = 'monthly', roi_gdf: Optional[geopandas.GeoDataFrame] = None, scale: Optional[int] = None) -> pandas.DataFrame

   Compute a time series of Land Surface Temperature (LST) statistics over a region of interest 
   using Google Earth Engine.

   This function retrieves LST data from a specified satellite, converts it to degrees Celsius, 
   aggregates it over regular time intervals (weekly, monthly, or yearly), and computes multiple 
   spatial statistics (mean, median, min, max) for each period. Output column names are standardized 
   across satellites for consistency.

   Parameters
   ----------
   start_date : str
       Start date of the time series in 'YYYY-MM-DD' format.
   end_date : str
       End date of the time series in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite data source. Supported options:
       - "MODIS" (MOD11A1)
       - "LANDSAT8" or "LC08" (Landsat 8 C2 L2)
       - "LANDSAT9" or "LC09" (Landsat 9 C2 L2)
       - "GCOM" (JAXA GCOM-C L3)
       (default: "MODIS").
   frequency : {"weekly", "monthly", "yearly"}, optional
       Temporal aggregation interval (default: "monthly").
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
       Must be provided; otherwise, a ValueError is raised.
   scale : int, optional
       Spatial resolution (in meters) for reduction. If omitted, a sensor-specific default is used:
       - MODIS: 1000 m
       - Landsat 8/9: 30 m
       - GCOM: 4638 m

   Returns
   -------
   pd.DataFrame
       A DataFrame where each row corresponds to one time period, with columns:
       - "date": Period start as "YYYY-MM-dd"
       - "satellite": Uppercase satellite name
       - "band": Original LST band name used (e.g., "LST_Day_1km")
       - "mean", "median", "min", "max": LST statistics in °C
       - "unit": Always "°C"
       Periods with no valid data (i.e., "mean" is null) are excluded.

   Raises
   ------
   ValueError
       If `roi_gdf` is not provided or if `frequency` is invalid.
       


