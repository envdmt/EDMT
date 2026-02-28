edmt.analysis.NDVI
==================

.. py:module:: edmt.analysis.NDVI




Module Contents
---------------

.. py:function:: get_ndvi_collection(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, dict]

   Retrieve a preprocessed Earth Engine ImageCollection containing NDVI (Normalized Difference 
   Vegetation Index) values, along with metadata parameters.

   The output collection contains a single band named "NDVI" with float values in the range [-1, 1]. 
   Raw data is scaled appropriately per sensor, and basic quality filtering is applied where needed.

   Parameters
   ----------
   satellite : str
       Satellite platform or product name. Supported options:
       - "LANDSAT", "LANDSAT_8DAY", or "LANDSAT8DAY": Uses precomputed 8-day Landsat NDVI composites 
         (Collection 2 Tier 1).
       - "MODIS": Uses MOD13Q1 (16-day L3 global 250m); values scaled by 0.0001.
       - "SENTINEL", "SENTINEL2", or "S2": Uses Sentinel-2 Harmonized (COPERNICUS/S2_HARMONIZED); 
         reflectance divided by 10,000; images with >60% cloud cover are excluded.
       - "VIIRS", "NOAA_VIIRS", or "NOAA": Uses NOAA CDR VIIRS NDVI V1; invalid values (-9998) masked, 
         values scaled by 0.0001.
   start_date : str
       Start date in 'YYYY-MM-DD' format.
   end_date : str
       End date in 'YYYY-MM-DD' format.

   Returns
   -------
   tuple[ee.ImageCollection, dict]
       - **ImageCollection**: Temporally filtered collection of NDVI images, each with a "NDVI" band 
         and preserved "system:time_start" property.
       - **params**: Dictionary with keys:
           - "band": Name of the NDVI band ("NDVI")
           - "unit": Unit identifier ("NDVI")

   Raises
   ------
   ValueError
       If the provided satellite name is not supported.



.. py:function:: compute_period_feature_ndvi(start: ee.Date, collection: ee.ImageCollection, geometry: ee.Geometry, frequency: str, satellite: str, scale: Optional[int] = None) -> ee.Feature

   Compute the mean NDVI over a specified time period and spatial region, returning a feature with metadata.

   This function aggregates NDVI images within a temporal window (weekly, monthly, or yearly), computes 
   the spatial mean over a region of interest, and includes the number of contributing images.

   Parameters
   ----------
   start : ee.Date
       Start date of the aggregation period.
   collection : ee.ImageCollection
       An ImageCollection containing a band named "NDVI" with values in the range [-1, 1].
   geometry : ee.Geometry
       Region of interest over which to compute the spatial mean.
   frequency : {"weekly", "monthly", "yearly"}
       Temporal interval defining the period length. Determines the end date via Earth Engine’s 
       calendar-aware `advance()` method.
   satellite : str
       Satellite name used to infer default spatial resolution if `scale` is not provided. 
       Supported: "LANDSAT", "LANDSAT_8DAY", "MODIS", "SENTINEL2", "VIIRS", etc.
   scale : int, optional
       Spatial resolution (in meters) for the reduction. If omitted, a sensor-specific default is used:
       - Landsat products: 30 m
       - MODIS & VIIRS: 500 m
       - Sentinel-2: 10 m

   Returns
   -------
   ee.Feature
       A feature with no geometry and the following properties:
       - "date": Period start formatted as "YYYY-MM-dd"
       - "ndvi": Mean NDVI value over the geometry (or `null` if no valid pixels)
       - "n_images": Number of images in the period used for compositing

   Raises
   ------
   ValueError
       If `frequency` is not one of "weekly", "monthly", or "yearly".
       


.. py:function:: compute_ndvi_timeseries(start_date: str, end_date: str, satellite: str = 'LANDSAT', frequency: str = 'monthly', roi_gdf: Optional[geopandas.GeoDataFrame] = None, scale: Optional[int] = None) -> pandas.DataFrame

   Compute a time series of mean NDVI values over a region of interest using Google Earth Engine.

   This function retrieves preprocessed NDVI data from a specified satellite product, aggregates 
   it over regular time intervals (weekly, monthly, or yearly), and computes the spatial mean for 
   each period. It also reports the number of images used per period.

   Parameters
   ----------
   start_date : str
       Start date of the time series in 'YYYY-MM-DD' format.
   end_date : str
       End date of the time series in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite or product name. Supported options:
       - "LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY": 8-day Landsat NDVI composites
       - "MODIS": MOD13Q1 (16-day, 250m)
       - "SENTINEL", "SENTINEL2", "S2": Sentinel-2 Harmonized
       - "VIIRS", "NOAA_VIIRS", "NOAA": NOAA CDR VIIRS NDVI
       (default: "LANDSAT").
   frequency : {"weekly", "monthly", "yearly"}, optional
       Temporal aggregation interval (default: "monthly").
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
       Must be provided; otherwise, a ValueError is raised.
   scale : int, optional
       Spatial resolution (in meters) for reduction. If omitted, a sensor-specific default is used:
       - Landsat: 30 m
       - MODIS & VIIRS: 500 m
       - Sentinel-2: 10 m

   Returns
   -------
   pd.DataFrame
       A DataFrame with one row per time period, containing:
       - "date": Period start as "YYYY-MM-dd"
       - "ndvi": Mean NDVI value (range [-1, 1]); `NaN` if no valid data
       - "n_images": Number of source images contributing to the period composite
       - "satellite": Uppercase satellite/product name
       - "unit": Always "NDVI"

   Raises
   ------
   ValueError
       If `roi_gdf` is not provided or if `frequency` is invalid.



