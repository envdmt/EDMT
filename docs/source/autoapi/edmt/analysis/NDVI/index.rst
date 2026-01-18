edmt.analysis.NDVI
==================

.. py:module:: edmt.analysis.NDVI




Module Contents
---------------

.. py:function:: get_ndvi_collection(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, dict]

   Retrieve a preprocessed Earth Engine ImageCollection containing NDVI (Normalized Difference 
   Vegetation Index) values, along with metadata parameters.

   The output collection contains a single band named "NDVI" with float values in the range [-1, 1]. 
   Raw reflectance data is scaled appropriately per sensor, and cloud masking is applied where supported.

   - **MODIS**: NDVI is scaled by 0.0001 (as per product specification).
   - **Landsat 8/9**: Surface reflectance bands are scaled using:  
     `reflectance = DN * 0.0000275 - 0.2`. Cloud, shadow, cirrus, and fill pixels are masked using QA_PIXEL.
   - **Sentinel-2**: Reflectance values are divided by 10,000. Images with >60% cloud cover are excluded, 
     and additional pixel-level cloud/cirrus masking is applied via QA60.

   Parameters
   ----------
   satellite : str
       Satellite platform. Supported options:
       - "MODIS": Uses MOD13Q1 (16-day L3 global 250m)
       - "LANDSAT": Merges Landsat 8 & 9 Collection 2 Level 2 SR
       - "SENTINEL", "SENTINEL2", or "S2": Uses Sentinel-2 SR Harmonized (COPERNICUS/S2_SR_HARMONIZED)
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

   Compute the mean NDVI over a specified time period and spatial region.

   This function aggregates NDVI values from an ImageCollection over a given temporal interval 
   (weekly, monthly, or yearly) and computes the spatial mean across a provided geometry.

   Parameters
   ----------
   start : ee.Date
       Start date of the aggregation period.
   collection : ee.ImageCollection
       An ImageCollection containing a single "NDVI" band with values in the range [-1, 1].
   geometry : ee.Geometry
       Region of interest over which to compute the spatial mean.
   frequency : {"weekly", "monthly", "yearly"}
       Temporal aggregation interval. Determines the end date of the period.
   satellite : str
       Satellite name used to infer default spatial resolution if `scale` is not provided. 
       Supported: "MODIS", "LANDSAT", "SENTINEL", "SENTINEL2", or "S2".
   scale : int, optional
       Spatial resolution (in meters) for the reduction. If omitted, a sensor-appropriate 
       default is used (MODIS: 250 m, Landsat: 30 m, Sentinel-2: 10 m).

   Returns
   -------
   ee.Feature
       A feature with no geometry and two properties:
       - "date": Start date of the period formatted as "YYYY-MM-dd".
       - "ndvi_mean": Mean NDVI value over the geometry during the period. 
         Set to `null` if no valid pixels are available.

   Raises
   ------
   ValueError
       If `frequency` is not supported or if `satellite` is unknown and `scale` is not provided.

   Notes
   -----
   - Uses `ee.Reducer.mean()` with a high `maxPixels` limit (1e13) to support large regions.
   - Temporal period boundaries are defined using Earth Engine’s calendar-aware `advance()` method.
   - The input collection must already be processed to contain only the "NDVI" band.


.. py:function:: compute_ndvi_timeseries(start_date: str, end_date: str, satellite: str = 'MODIS', frequency: str = 'monthly', roi_gdf: Optional[geopandas.GeoDataFrame] = None, scale: Optional[int] = None) -> pandas.DataFrame

   Compute a time series of mean Normalized Difference Vegetation Index (NDVI) over a region 
   of interest using Google Earth Engine.

   The function retrieves NDVI data from a specified satellite sensor, aggregates it over 
   regular time intervals (weekly, monthly, or yearly), and returns the results as a pandas DataFrame.

   Parameters
   ----------
   start_date : str
       Start date of the time series in 'YYYY-MM-DD' format.
   end_date : str
       End date of the time series in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite data source. Supported options: 
       - "MODIS" (MOD13Q1)
       - "LANDSAT" (Landsat 8 & 9 Collection 2 Level 2 SR)
       - "SENTINEL", "SENTINEL2", or "S2" (Sentinel-2 SR Harmonized)
       (default: "MODIS").
   frequency : str, optional
       Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly" 
       (default: "monthly").
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
       Must be provided; otherwise, a ValueError is raised.
   scale : int, optional
       Spatial resolution (in meters) for the reduction operation. If not provided, 
       a sensor-appropriate default is used (MODIS: 250 m, Landsat: 30 m, Sentinel-2: 10 m).

   Returns
   -------
   pd.DataFrame
       A DataFrame with the following columns:
       - "date": Start date of each period as "YYYY-MM-dd".
       - "ndvi_mean": Mean NDVI value (range [-1, 1]) over the ROI during that period.
       - "satellite": Name of the satellite used (uppercase).
       - "unit": Unit identifier (always "NDVI").
       Periods with no valid NDVI data (e.g., due to clouds or missing imagery) are excluded.

   Raises
   ------
   ValueError
       If `roi_gdf` is not provided or if `frequency` is invalid.

   Notes
   -----
   - Internally uses `get_ndvi_collection` to fetch and preprocess NDVI data, including cloud masking.
   - The collection is pre-filtered to the ROI using `filterBounds` to improve performance.
   - Time steps are approximated using fixed day counts (7, 30, or 365 days); calendar alignment 
     may vary slightly for monthly/yearly intervals.


