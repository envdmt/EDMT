edmt.models.drones
==================

.. py:module:: edmt.models.drones








Module Contents
---------------

.. py:data:: logger

.. py:data:: geod

.. py:class:: Airdata(api_key)



   Client for interacting with the Airdata API.
   Handles authentication and provides methods to fetch various data types
   such as flights,flight groups, drones, batteries, and pilots.


   .. py:method:: AccessGroups(endpoint: str) -> Optional[pandas.DataFrame]


   .. py:method:: AccessItems(endpoint: str) -> Optional[pandas.DataFrame]

      Sends a GET request to the specified API endpoint and returns normalized data as a DataFrame.

      Parameters:
          endpoint (str): The full API path including query parameters.

      Returns:
          Optional[pd.DataFrame]: A DataFrame containing the retrieved data, or None if the request fails.



   .. py:method:: get_drones() -> pandas.DataFrame

      Fetch drone data from the Airdata API based on the provided query parameters.


      Returns:
          pd.DataFrame: A DataFrame containing the retrieved flight data. 
                      If the request fails or no data is found, returns an empty DataFrame.



   .. py:method:: get_batteries() -> pandas.DataFrame

      Fetch batteries data from the Airdata API based on the provided query parameters.


      Returns:
          pd.DataFrame: A DataFrame containing the retrieved flight data. 
                      If the request fails or no data is found, returns an empty DataFrame.



   .. py:method:: get_pilots() -> pandas.DataFrame

      Fetch pilots data from the Airdata API based on the provided query parameters.


      Returns:
          pd.DataFrame: A DataFrame containing the retrieved flight data. 
                      If the request fails or no data is found, returns an empty DataFrame.



   .. py:method:: get_flightgroups(sort_by: str = None, ascending: bool = True) -> pandas.DataFrame

      Fetch Flight Groups data from the Airdata API based on query parameters.

      Parameters:
          sort_by (str, optional): Field to sort by. Valid values are 'title' and 'created'.
                                   If None, no sorting is applied.
          ascending (bool): Whether to sort in ascending order. Defaults to True.
          id (str, optional): Specific ID of a flight group to fetch.

      Returns:
          pd.DataFrame: DataFrame containing retrieved flight data.
                        Returns empty DataFrame if request fails or no data found.



   .. py:method:: get_flights(since: Optional[str] = None, until: Optional[str] = None, created_after: Optional[str] = None, battery_ids: Optional[Union[str, List[str]]] = None, pilot_ids: Optional[Union[str, List[str]]] = None, location: Optional[List[float]] = None, limit: int = 100, max_pages: int = 100, delay: float = 0.1, timeout: int = 15) -> pandas.DataFrame

      Retrieve paginated flight records from the Airdata API.

      Fetches flight data by automatically handling offset-based pagination across
      multiple API requests. Continues until no more results are returned or the
      maximum page limit is reached.

      Args:
          since (str, optional): 
              Filter flights that started on or after this ISO 8601 timestamp
          until (str, optional): 
              Filter flights that started before this ISO 8601 timestamp.
          created_after (str, optional): 
              Include only flights created after this ISO 8601 timestamp.
          battery_ids (str or list, optional): 
              Filter by specific battery ID(s). Accepts either a comma-separated 
              string or a list of strings
          pilot_ids (str or list, optional): 
              Filter by specific pilot ID(s).
          location (list, optional): 
              Geographic center point for radius-based search as 
              ``[latitude, longitude]``.
          limit (int, optional): 
              Number of records per page. Must be ≤ 100. Defaults to 100.
          max_pages (int, optional): 
              Maximum number of pages to retrieve. Prevents excessive API usage. 
              Defaults to 100.

      Returns:
          pd.DataFrame: 
              A DataFrame containing all retrieved flight records with standardized 
              columns. Returns an empty DataFrame if:
              
              - No flights match the query parameters
              - API returns an error
              - Authentication fails

      Raises:
          ValueError: 
              If ``location`` is provided but doesn't contain exactly two numeric 
              elements (latitude and longitude).



.. py:function:: _flight_polyline(row, link_col='csvLink', lon_col='longitude', lat_col='latitude', time_col='time(millisecond)', max_retries=3, timeout=15)

   Processes a single flight metadata record by downloading its telemetry CSV, 
   cleaning the trajectory data, and constructing a geographic LineString.

   This function:
   - Fetches a CSV file from the 'csvLink' field in `row` using `AirdataCSV`.
   - Validates that the required columns (`lon_col`, `lat_col`, `time_col`) exist.
   - Filters out invalid coordinates (e.g., (0, 0)).
   - Sorts points by timestamp and ensures at least two valid points remain.
   - Constructs a `shapely.geometry.LineString` from the cleaned coordinates.
   - Computes the total geodesic distance (in meters) along the trajectory using the WGS84 ellipsoid.
   - Returns a dictionary containing the original flight metadata (excluding 'csvLink'), 
     enriched with geometry and derived metrics.

   Args:
       row (pandas.Series or dict): A flight metadata record expected to contain 
           a valid URL under the key 'csvLink' and a unique identifier under 'id'.
       lon_col (str, optional): Column name for longitude values in the CSV. 
           Defaults to "longitude".
       lat_col (str, optional): Column name for latitude values in the CSV. 
           Defaults to "latitude".
       time_col (str, optional): Column name for timestamp values (in milliseconds). 
           Defaults to "time(millisecond)".
       max_retries (int, optional): Maximum number of download retry attempts. 
           Passed to `AirdataCSV`. Defaults to 3.
       timeout (int or float, optional): Request timeout (in seconds) for CSV download. 
           Passed to `AirdataCSV`. Defaults to 15.

   Returns:
       dict or None:
           - If successful: a dictionary with the following keys:
               - All original metadata fields from `row` (except 'csvLink'),
               - "id": flight identifier,
               - "geometry": `shapely.geometry.LineString` of the flight path,
               - "flight_distance_m": total geodesic distance in meters (float),
               - "flight_time_max_ms": maximum timestamp in the cleaned CSV (int/float).
           - `None` if the URL is missing/invalid, required columns are absent, 
             fewer than two valid points remain after cleaning, or an unhandled 
             exception occurs during processing.


.. py:function:: get_flight_routes(df: pandas.DataFrame, filter_ids: Optional[List] = None, max_workers: int = 8, lon_col: str = 'longitude', lat_col: str = 'latitude', time_col: str = 'time(millisecond)', crs: str = 'EPSG:4326') -> geopandas.GeoDataFrame

   Extract flight routes from a DataFrame containing flight metadata and CSV URLs.

   This function processes each flight record in the input DataFrame, retrieves
   the associated CSV file containing flight data, and computes the flight route
   as a LineString geometry. It supports filtering by specific flight IDs and
   parallel processing for efficiency.

   Args:
       df (pd.DataFrame): DataFrame containing flight metadata, including a column
           named 'csvLink' with URLs to CSV files.
       filter_ids (list, optional): List of flight IDs to process. If provided,
           only flights with IDs in this list will be processed.   
       max_workers (int, optional): Number of parallel download threads.

       lon_col (str, optional): Column name for longitude.
       lat_col (str, optional): Column name for latitude.
       time_col (str, optional): Column name for timestamp.
       crs (str, optional): Coordinate Reference System for the output GeoDataFrame.   
   Returns:
       gpd.GeoDataFrame: A GeoDataFrame with one row per flight, containing the
           flight metadata and a LineString geometry representing the flight route.


.. py:function:: airPoint(df: pandas.DataFrame, filter_ids: Optional[List] = None, link_col: str = 'csvLink', max_retries: int = 3, timeout: int = 10, chunk_size: int = 100, max_workers: int = 20) -> geopandas.GeoDataFrame

   Download and extract point-based telemetry data from CSV links into a GeoDataFrame.

   This function processes a DataFrame containing metadata records and URLs to
   CSV files with telemetry data (e.g., GPS points). Each CSV is downloaded in
   parallel, merged with its corresponding metadata, and combined into a single
   GeoDataFrame of point geometries.

   The function supports optional filtering by record IDs, chunked processing
   for large datasets, retry logic for unstable network requests, and progress
   tracking via nested progress bars.

   Args:
       df (pd.DataFrame): Input DataFrame containing metadata for each record.
           Must include an ``id`` column and a column with CSV URLs.
       filter_ids (list, optional): List of IDs to process. If provided, only
           rows whose ``id`` is in this list will be processed.
       link_col (str, optional): Name of the column containing CSV URLs.
           Defaults to ``"csvLink"``.
       max_retries (int, optional): Maximum number of retry attempts for failed
           CSV downloads. Defaults to 3.
       timeout (int, optional): Timeout in seconds for each CSV download request.
           Defaults to 10.
       chunk_size (int, optional): Number of rows to process per chunk. Chunking
           is automatically enabled when the input DataFrame exceeds this size.
           Defaults to 100.
       max_workers (int, optional): Number of parallel worker threads used for
           downloading and processing CSV files. Defaults to 20.

   Returns:
       gpd.GeoDataFrame: A GeoDataFrame containing the merged metadata and
       telemetry records, with point geometries created from ``longitude`` and
       ``latitude`` columns using CRS ``EPSG:4326``.

       If no valid telemetry data is retrieved, an empty GeoDataFrame is returned.

   Raises:
       ValueError: If required columns (``id`` or the CSV link column) are missing.
       ValueError: If ``longitude`` and ``latitude`` columns are not present in
       the extracted telemetry data.


.. py:function:: airLine(gdf: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame

   Aggregate point-based flight telemetry into line geometries with distance metrics.

   This function converts a GeoDataFrame of point-based telemetry (e.g. GPS fixes)
   into one LineString per flight by ordering points temporally and connecting
   them in sequence. Sorting and grouping are performed using DuckDB to improve
   performance and reduce memory usage for large datasets.

   Invalid geometries at (0, 0) are removed, coordinates are normalized to
   EPSG:4326, and total flight distance is computed using geodesic calculations.

   Args:
       gdf (gpd.GeoDataFrame): GeoDataFrame containing point geometries and
           flight telemetry. Must include:
           - ``id``: unique flight identifier
           - ``geometry``: Point geometries
           - ``time(millisecond)``: timestamp used to order points

   Returns:
       gpd.GeoDataFrame: A GeoDataFrame with one row per flight, containing:
           - original flight metadata
           - ``geometry`` as a LineString representing the flight path
           - ``airline_distance_m``: total geodesic distance in meters
           - ``airline_time``: final timestamp for the flight

       If no valid flight paths can be constructed, an empty GeoDataFrame is returned.

   Raises:
       ValueError: If required columns are missing from the input GeoDataFrame.


.. py:function:: airSegment(gdf: geopandas.GeoDataFrame) -> geopandas.GeoDataFrame

   Convert point-based flight trajectories into consecutive line segments.

   This function transforms a GeoDataFrame of ordered point telemetry into
   individual LineString segments representing movement between consecutive
   points for each flight ``id``. Each segment includes distance, duration,
   and timing metadata, enabling fine-grained movement and speed analysis.

   Sorting and window operations are performed using DuckDB to efficiently
   compute consecutive point pairs while minimizing memory usage. Geodesic
   distance is calculated in meters using WGS84 coordinates.

   Args:
       gdf (gpd.GeoDataFrame): GeoDataFrame containing point geometries and
           telemetry attributes. Must include:
           - ``id``: unique trajectory or flight identifier
           - ``geometry``: Point geometries
           - ``time(millisecond)``: timestamp used to order points

   Returns:
       gpd.GeoDataFrame: A GeoDataFrame where each row represents a single
       trajectory segment, including:
           - ``geometry``: LineString between consecutive points
           - ``segment_distance_m``: geodesic distance in meters
           - ``segment_duration_ms``: time difference between points
           - ``segment_start_time`` and ``segment_end_time``
           - original metadata columns propagated from the source data

       If no valid segments can be generated, an empty GeoDataFrame is returned.

   Raises:
       ValueError: If required columns are missing from the input GeoDataFrame.


