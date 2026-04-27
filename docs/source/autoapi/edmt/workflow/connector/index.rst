edmt.workflow.connector
=======================

.. py:module:: edmt.workflow.connector




Module Contents
---------------

.. py:function:: get_satellite_collection(product, satellite=None, start_date=None, end_date=None)

   Retrieve an Earth Engine ImageCollection and metadata for a supported environmental data product.

   This function serves as a unified entry point to access preconfigured satellite or gridded 
   datasets (e.g., NDVI, LST, precipitation) by delegating to specialized internal pipelines. 
   It returns both the raw image collection and a dictionary of processing parameters.

   Parameters
   ----------
   product : str
       Name of the environmental data product. Supported values include:
       - Vegetation indices: "NDVI", "EVI"
       - Land Surface Temperature: "LST"
       - Precipitation: "CHIRPS"
       (Case-insensitive; aliases are normalized internally.)
   satellite : str, optional
       Satellite platform or sensor (e.g., "MODIS", "LANDSAT", "SENTINEL2"). 
       Required for vegetation and LST products; ignored for grid-based products like CHIRPS.
   start_date : str, optional
       Start date in 'YYYY-MM-DD' format. Required if `end_date` is provided.
   end_date : str, optional
       End date in 'YYYY-MM-DD' format. Required if `start_date` is provided.

   Returns
   -------
   tuple[ee.ImageCollection, dict]
       - **ImageCollection**: Filtered and preprocessed Earth Engine image collection.
       - **meta**: Dictionary containing:
           - Product-specific scaling factors, band names, and units
           - Input arguments: `"product"`, `"satellite"`, `"start_date"`, `"end_date"`

   Raises
   ------
   ValueError
       If `product` is not supported or if required arguments are missing for the selected pipeline.

   Notes
   -----
   - Date filtering is applied during collection construction.
   - No cloud masking, quality filtering, or unit conversion is performed beyond what is 
     defined in the underlying pipeline.
   - All collections preserve native temporal and spatial metadata for downstream use.


.. py:function:: compute_period_feature(product: str, start: ee.Date, collection: ee.ImageCollection, geometry: ee.Geometry, frequency: str, meta: Dict[str, Any], scale: Optional[int] = None) -> ee.Feature

   Compute spatial summary statistics for a given environmental product 
   over a time period and region of interest, returning an Earth Engine Feature.

   This function aggregates images in the input collection over a temporal window (defined by `start` 
   and `frequency`), computes statistics over `geometry`, and packages results into a feature with 
   standardized properties—including product-specific metadata from `meta`.

   Parameters
   ----------
   product : str
       Environmental product name (e.g., "NDVI", "LST", "CHIRPS"). Used to select appropriate 
       statistic computation logic.
   start : ee.Date
       Start date of the aggregation period.
   collection : ee.ImageCollection
       Pre-filtered ImageCollection containing the relevant band(s).
   geometry : ee.Geometry
       Region of interest for spatial reduction.
   frequency : {"daily", "weekly", "monthly", "yearly"}
       Temporal interval defining the period length. Determines end date.
   meta : dict
       Metadata dictionary (typically from `get_satellite_collection`) containing at least:
       - `"scale_m"`: default spatial resolution (in meters)
       - `"band"`: primary band name (e.g., "NDVI")
       - `"unit"`: measurement unit (e.g., "NDVI", "°C", "mm")
       Additional keys may be used by `_compute`.
   scale : int, optional
       Spatial resolution (in meters) for reduction. If omitted, defaults to `meta["scale_m"]`.

   Returns
   -------
   ee.Feature
       A feature with no geometry and the following properties:
       - `"date"`: Period start formatted as "YYYY-MM-dd"
       - `"product"`: Uppercase product name
       - `"band"`: Band name used (from `meta`)
       - `"unit"`: Unit of measurement (from `meta`)
       - `"n_images"`: Number of images in the period
       - Statistic keys (e.g., `"mean"`, `"median"`, `"min"`, `"max"`) — values are `null` if no data.

   Raises
   ------
   ValueError
       If `scale` is missing and `meta["scale_m"]` is not present or invalid.

   Notes
   -----
   - For empty periods (no images), returns a feature with `"n_images": 0` and all statistics as `null`.
   - Geometry is reprojected to the image’s native CRS before reduction for accuracy.
   - Designed for use in time-series generation (e.g., mapping over date sequences).


.. py:function:: ComputeTimeseries(product: str, start_date: str, end_date: str, frequency: str, roi_gdf: geopandas.GeoDataFrame, satellite: Optional[str] = None, scale: Optional[int] = None) -> pandas.DataFrame

   Generate a time series of environmental metrics (e.g., NDVI, LST, precipitation) over a region of interest.

   This function retrieves satellite or gridded data for a specified product, aggregates it over regular 
   time intervals (daily, weekly, monthly, or yearly), computes spatial statistics,and returns results as 
   a pandas DataFrame with standardized columns.

   Parameters
   ----------
   product : str
       Environmental product to retrieve. Supported values include:
       - "NDVI", "EVI" (vegetation indices)
       - "LST" (Land Surface Temperature)
       - "CHIRPS" (precipitation)
   start_date : str
       Start date of the time series in 'YYYY-MM-DD' format.
   end_date : str
       End date of the time series in 'YYYY-MM-DD' format.
   frequency : {"daily", "weekly", "monthly", "yearly"}
       Temporal aggregation interval.
   roi_gdf : geopandas.GeoDataFrame
       Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries.
       Must be provided; cannot be None.
   satellite : str, optional
       Satellite platform (e.g., "MODIS", "LANDSAT", "SENTINEL2"). Required for vegetation and LST products.
       Ignored for grid-based products like CHIRPS.
   scale : int, optional
       Spatial resolution (in meters) for reduction. If omitted, a product- and sensor-appropriate default 
       is used (e.g., 500 m for MODIS LST, 10 m for Sentinel-2).

   Returns
   -------
   pd.DataFrame
       A DataFrame with one row per time period, containing:
       - `"date"`: Period start as "YYYY-MM-dd"
       - `"product"`: Uppercase product name
       - `"satellite"`: Satellite name (if applicable)
       - Statistic columns (e.g., `"mean"`, `"median"`, `"ndvi"`, `"precipitation_mm"`)
       - `"n_images"`: Number of source images used per period
       - `"unit"`: Measurement unit (e.g., "NDVI", "°C", "mm")
       - (Optional) `"month"`: Full month name (e.g., "January") if `frequency="monthly"`

       Rows with all-null statistics are removed based on product-specific logic.

   Raises
   ------
   ValueError
       If `roi_gdf` is not provided.

   Notes
   -----
   - For MODIS products, the ROI geometry is reprojected to the native sinusoidal projection 
     to ensure accurate spatial reduction.
   - The collection is pre-filtered to the ROI using `filterBounds` for performance.
   - Time periods are generated using calendar-aware intervals (not fixed day counts).
   - Missing or invalid data points are filtered out post-reduction based on the primary metric:
       - LST: removes rows where `"mean"` is null
       - CHIRPS: removes rows where `"precipitation_mm"` is null
       - Vegetation indices: removes rows where the index column (`"ndvi"`, `"evi"`) is null
   - Requires an initialized Earth Engine session (`ee.Initialize()`); ensured via `ee_initialized()`.


.. py:function:: CompositeImage(product: str, start_date: str, end_date: str, satellite: Optional[str] = None, roi_gdf: Optional[geopandas.GeoDataFrame] = None, reducer: str = 'mean') -> ee.Image

   Generate a single composite Earth Engine image by aggregating a time series of environmental data.

   This function retrieves a filtered ImageCollection for the specified product and time range, 
   applies a temporal reducer (e.g., mean, median), and optionally clips the result to a region of interest.

   Parameters
   ----------
   product : str
       Environmental product name (e.g., "NDVI", "LST", "CHIRPS", "EVI"). Case-insensitive; normalized internally.
   start_date : str
       Start date in 'YYYY-MM-DD' format.
   end_date : str
       End date in 'YYYY-MM-DD' format.
   satellite : str, optional
       Satellite platform (e.g., "MODIS", "LANDSAT", "SENTINEL2"). Required for sensor-based products; 
       ignored for gridded datasets like CHIRPS.
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame. If provided, the output image is clipped to this geometry.
   reducer : {"mean", "median", "min", "max"}, optional
       Temporal aggregation method applied across the time series (default: "mean").

   Returns
   -------
   ee.Image
       A single-band (or multi-band) composite image with:
       - Band name(s) preserved from the source collection (e.g., "NDVI", "LST_C")
       - Properties including:
           - `"product"`: normalized product name
           - `"satellite"`: satellite used (if applicable)
           - `"start_date"`, `"end_date"`: time range
           - `"reducer"`: aggregation method
           - `"unit"`: measurement unit (e.g., "NDVI", "°C", "mm")

   Notes
   -----
   - Uses internally to handle product-specific compositing logic.
   - For MODIS, the ROI geometry is reprojected to the native projection before clipping (if `roi_gdf` is provided).
   - The input collection is pre-filtered to the ROI using `filterBounds` for efficiency.
   - No cloud masking or quality filtering is applied beyond what is defined in `get_satellite_collection`.
   - Requires an initialized Earth Engine session (`ee.Initialize()`); ensured via `ee_initialized()`.


.. py:function:: CollectionImage(product: str, start_date: str, end_date: str, frequency: edmt.workflow.builder.Frequency = 'monthly', satellite: Optional[str] = None, roi_gdf: Optional[geopandas.GeoDataFrame] = None, reducer: edmt.workflow.builder.ReducerName = 'mean') -> ee.ImageCollection

   Generate an Earth Engine ImageCollection of temporally aggregated composites over regular intervals.

   This function divides the input date range into periods, aggregates imagery 
   within each period using a specified reducer, and returns a time-series ImageCollection suitable 
   for animation, charting, or further analysis.

   Parameters
   ----------
   product : str
       Environmental data product. Supported values include:
       - Vegetation: "NDVI", "EVI"
       - Temperature: "LST"
       - Precipitation: "CHIRPS"
       (Case-insensitive; normalized internally.)
   start_date : str
       Start date in 'YYYY-MM-DD' format.
   end_date : str
       End date in 'YYYY-MM-DD' format.
   frequency : {"daily", "weekly", "monthly", "yearly"}, optional
       Temporal interval for compositing (default: "monthly").
   satellite : str, optional
       Satellite platform (e.g., "MODIS", "LANDSAT", "SENTINEL2"). Required for sensor-based products; 
       ignored for gridded datasets like CHIRPS.
   roi_gdf : geopandas.GeoDataFrame, optional
       Region of interest as a GeoDataFrame. If provided, the collection is filtered to this region 
       and output images are clipped to it.
   reducer : {"mean", "median", "min", "max", "sum"}, optional
       Temporal aggregation method. For "CHIRPS", "sum" is allowed (for total precipitation); 
       other products support only statistical reducers (default: "mean").

   Returns
   -------
   ee.ImageCollection
       An ImageCollection where each image:
       - Represents one time period (e.g., January 2023)
       - Contains band(s) named per the source product
       - Has properties:
           - `"system:time_start"`: period start (milliseconds since Unix epoch)
           - `"period_start"`: formatted as "YYYY-MM-dd"
           - `"product"`, `"satellite"`, `"frequency"`, `"reducer"`, `"unit"`
       - (For monthly frequency) Includes a `"month"` property with full month name (e.g., "January")

   Raises
   ------
   ValueError
       If an unsupported reducer is specified for the given product (e.g., "sum" for NDVI).

   Notes
   -----
   - For MODIS vegetation products, the ROI geometry is reprojected to the native sinusoidal projection 
     before filtering and clipping to ensure spatial accuracy.
   - The collection is pre-filtered to the ROI (if provided) for performance.
   - Time periods are generated using calendar-aware intervals (not fixed day counts).
   - CHIRPS supports `"sum"` to compute total precipitation over the period; all other products use 
     pixel-wise statistics (mean, median, etc.).
   - Requires an initialized Earth Engine session (`ee.Initialize()`); ensured via `ee_initialized()`.


.. py:function:: ee_to_points(image: ee.Image, scale: int = 30, num_pixels: int = 5000) -> geopandas.GeoDataFrame

   Sample pixel values from an Earth Engine image and return them as a GeoDataFrame.

   This function extracts a uniform random subset of pixels from the input ``ee.Image`` 
   at a specified spatial resolution. Each sampled pixel is converted to a point geometry 
   with its corresponding band values stored as attributes. The resulting data is 
   downloaded synchronously and formatted as a ``geopandas.GeoDataFrame`` with 
   WGS84 (EPSG:4326) projection.

   Args:
       image (ee.Image): The input Earth Engine image to sample. Must be a valid, 
           initialized Earth Engine image object.
       scale (int, optional): The nominal scale in meters at which to sample the image. 
           Defaults to ``30``. Should closely match the native resolution of the target 
           bands for accurate value extraction.
       num_pixels (int, optional): The maximum number of pixels to sample. Defaults to 
           ``5000``. Earth Engine will return up to this number (or fewer if the image 
           contains fewer valid/unmasked pixels).
           
   Returns:
       gpd.GeoDataFrame: A GeoDataFrame where each row represents a sampled pixel. 
           Columns include the point geometry (named ``geometry``) and one column per 
           image band containing the sampled values. The coordinate reference system 
           (CRS) is explicitly set to ``EPSG:4326``.
           
   Raises:
       ee.EEException: If the image is invalid, the scale is unsupported, Earth Engine 
           computation times out, or the response payload exceeds the ``getInfo()`` limit.
           
         
   Example:
       >>> import ee
       >>> import geopandas as gpd
       >>> ee.Initialize()
       >>> img = ee.Image('COPERNICUS/S2_SR/20230615T123456').select(['B4', 'B8'])
       >>> gdf = ee_to_points(img, scale=10, num_pixels=1000)
       >>> print(gdf.head())
       >>> print(gdf.crs)  # EPSG:4326


