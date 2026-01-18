edmt.analysis.LST
=================

.. py:module:: edmt.analysis.LST




Module Contents
---------------

.. py:function:: get_satellite_collection(satellite: str, start_date: str, end_date: str) -> tuple[ee.ImageCollection, dict]

   Retrieve an Earth Engine ImageCollection and associated scaling parameters 
   for land surface temperature (LST) from a specified satellite.

   Parameters
   ----------
   satellite : str
       Name of the satellite sensor. Supported options: "MODIS", "LANDSAT", "GCOM".
   start_date : str
       Start date for filtering the collection in 'YYYY-MM-DD' format.
   end_date : str
       End date for filtering the collection in 'YYYY-MM-DD' format.

   Returns
   -------
   tuple[ee.ImageCollection, dict]
       A tuple containing:
       - An ee.ImageCollection filtered to the specified date range and pre-selected band.
       - A dictionary with scaling factors (`multiply`, `add`) and the selected band name,
         used to convert raw digital numbers to physical LST values (in Kelvin).

   Raises
   ------
   ValueError
       If the provided satellite name is not supported.


.. py:function:: compute_period_feature(start: ee.Date, collection: ee.ImageCollection, geometry: ee.Geometry, frequency: str, satellite: str, scale: int = None) -> ee.Feature

   Compute the mean land surface temperature (LST) over a specified time period 
   (weekly, monthly, or yearly) for a given region, using a default scale per satellite
   if not provided.

   Parameters
   ----------
   start : ee.Date
       The start date of the aggregation period.
   collection : ee.ImageCollection
       An ImageCollection containing LST images (assumed to be in Kelvin or already scaled).
   geometry : ee.Geometry
       The region of interest over which to compute the spatial mean.
   frequency : str
       Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly".
   satellite : str
       Name of the satellite ("MODIS", "LANDSAT", "GCOM") to select default scale.
   scale : int, optional
       Spatial resolution (meters). If None, a default per satellite is used:
           MODIS: 1000
           LANDSAT: 30
           GCOM: 4638.3

   Returns
   -------
   ee.Feature
       A feature with no geometry and properties:
       - "date": Start date of the period as "YYYY-MM-dd".
       - "lst_mean": Mean LST value over the geometry. Null if no valid pixels.


.. py:function:: compute_lst_timeseries(start_date: str, end_date: str, satellite: str = 'MODIS', frequency: str = 'monthly', roi_gdf: Optional[geopandas.GeoDataFrame] = None, scale: Optional[int] = None) -> pandas.DataFrame

   Compute a time series of mean Land Surface Temperature (LST) over a region of interest 
   using Google Earth Engine (GEE) satellite data.

   The function retrieves LST data from a specified satellite sensor, converts it to degrees 
   Celsius, aggregates it over regular time intervals (weekly, monthly, or yearly), and returns 
   the results as a pandas DataFrame.

   Parameters
   ----------
   start_date : str
       Start date of the time series in 'YYYY-MM-DD' format.
   end_date : str
       End date of the time series in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
   frequency : str, optional
       Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly" 
       (default: "monthly").
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame containing a single Polygon or MultiPolygon geometry. 
       Must be provided; otherwise, a ValueError is raised.
   scale : int, optional
       Spatial resolution (in meters) for the reduction operation (default: 1000).

   Returns
   -------
   pd.DataFrame
       A DataFrame with columns:
       - "date": Start date of each period as "YYYY-MM-dd".
       - "lst_mean": Mean LST in degrees Celsius for that period.
       - "satellite": Name of the satellite used.
       - "unit": Always "°C".
       Rows with no valid LST data (e.g., due to cloud cover or missing imagery) are excluded.

   Raises
   ------
   ValueError
       If `roi_gdf` is not provided.



