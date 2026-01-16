edmt.analysis.LST
=================

.. py:module:: edmt.analysis.LST




Module Contents
---------------

.. py:function:: ensure_ee_initialized()

   Initialize Google Earth Engine if not already initialized.


.. py:function:: gdf_to_ee_geometry(gdf: geopandas.GeoDataFrame) -> ee.Geometry

   Convert a GeoDataFrame containing Polygon or MultiPolygon geometries to an Earth Engine Geometry.

   The input GeoDataFrame is reprojected to WGS84 (EPSG:4326) if necessary, and all geometries 
   are dissolved into a single geometry using unary union before conversion.

   Parameters
   ----------
   gdf : geopandas.GeoDataFrame
       A GeoDataFrame containing one or more Polygon or MultiPolygon features. 
       Must have a valid coordinate reference system (CRS).

   Returns
   -------
   ee.Geometry
       An Earth Engine Geometry object representing the union of all input geometries, 
       in WGS84 (longitude/latitude).

   Raises
   ------
   ValueError
       If the GeoDataFrame is empty or lacks a CRS.


.. py:function:: get_satellite_collection(satellite: str, start_date: str, end_date: str) -> tuple[ee.ImageCollection, dict]

   Retrieve an Earth Engine ImageCollection and associated scaling parameters 
   for land surface temperature (LST) from a specified satellite.

   Parameters
   ----------
   satellite : str
       Name of the satellite sensor. Supported options: "MODIS", "LANDSAT", or "GCOM".
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

   Notes
   -----
   Scaling equations:
     - MODIS (MOD11A1): LST = LST_Day_1km * 0.02
     - Landsat 8 (LC08 C02 T1_L2): LST = ST_B10 * 0.00341802 + 149.0
     - GCOM-C (JAXA): LST = LST_AVE * 0.02


.. py:function:: to_celsius(img: ee.Image, factors: dict) -> ee.Image

   Convert a raw land surface temperature (LST) image from digital numbers to degrees Celsius.

   The conversion applies satellite-specific scaling factors to transform raw pixel values 
   to Kelvin, then subtracts 273.15 to obtain Celsius.

   Parameters
   ----------
   img : ee.Image
       An Earth Engine image containing raw LST band values (e.g., "LST_Day_1km", "ST_B10").
   factors : dict
       A dictionary containing scaling parameters with keys:
       - "multiply" (float): Multiplicative scaling factor.
       - "add" (float): Additive offset.
       These are applied as: scaled_value = img * multiply + add.

   Returns
   -------
   ee.Image
       An image with LST values in degrees Celsius, preserving the original band name 
       and copying essential metadata (e.g., 'system:time_start').


.. py:function:: compute_period_feature(start: ee.Date, collection: ee.ImageCollection, geometry: ee.Geometry, scale: int, frequency: str) -> ee.Feature

   Compute the mean land surface temperature (LST) over a specified time period 
   (weekly, monthly, or yearly) for a given region.

   Parameters
   ----------
   start : ee.Date
       The start date of the aggregation period.
   collection : ee.ImageCollection
       An ImageCollection containing LST images (assumed to be in Kelvin or already scaled).
   geometry : ee.Geometry
       The region of interest over which to compute the spatial mean.
   scale : int
       The spatial resolution (in meters) at which to perform the reduction.
   frequency : str
       Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly".

   Returns
   -------
   ee.Feature
       A feature with no geometry and two properties:
       - "date": Formatted start date of the period as "YYYY-MM-dd".
       - "lst_mean": Mean LST value (in the same unit as input collection, typically Kelvin 
         unless pre-converted) over the geometry during the period. 
         If no valid pixels are available, the value is set to null.

   Raises
   ------
   ValueError
       If the `frequency` is not one of the supported options.


.. py:function:: compute_lst_timeseries(start_date: str, end_date: str, satellite: str = 'MODIS', frequency: str = 'monthly', roi_gdf: Optional[geopandas.GeoDataFrame] = None, scale: int = 1000) -> pandas.DataFrame

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



