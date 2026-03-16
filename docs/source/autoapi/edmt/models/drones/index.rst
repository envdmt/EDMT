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


.. py:function:: airPoint(*args, **kwargs)

.. py:function:: airLine(*args, **kwargs)

.. py:function:: airSegment(*args, **kwargs)

