edmt.models.drones
==================

.. py:module:: edmt.models.drones








Module Contents
---------------

.. py:data:: logger

.. py:data:: geod

.. py:class:: Airdata(api_key: str, skip_auth: bool = False)

   Bases: :py:obj:`edmt.base.base.AirdataBaseClass`


   Client for interacting with the Airdata API.
   Handles authentication and provides methods to fetch various data types
   such as flights,flight groups, drones, batteries, and pilots.


   .. py:method:: AccessGroups(endpoint: str) -> Optional[pandas.DataFrame]


   .. py:method:: AccessItems(endpoint: str) -> Optional[pandas.DataFrame]

      Sends a GET request to the specified API endpoint and returns normalized data as a DataFrame.

      :param endpoint: The full API path including query parameters.
      :type endpoint: str

      :returns: A DataFrame containing the retrieved data, or None if the request fails.
      :rtype: Optional[pd.DataFrame]



   .. py:method:: get_drones() -> pandas.DataFrame

      Fetch drone data from the Airdata API based on the provided query parameters.


      :returns:

                A DataFrame containing the retrieved flight data.
                            If the request fails or no data is found, returns an empty DataFrame.
      :rtype: pd.DataFrame



   .. py:method:: get_batteries() -> pandas.DataFrame

      Fetch batteries data from the Airdata API based on the provided query parameters.


      :returns:

                A DataFrame containing the retrieved flight data.
                            If the request fails or no data is found, returns an empty DataFrame.
      :rtype: pd.DataFrame



   .. py:method:: get_pilots() -> pandas.DataFrame

      Fetch pilots data from the Airdata API based on the provided query parameters.


      :returns:

                A DataFrame containing the retrieved flight data.
                            If the request fails or no data is found, returns an empty DataFrame.
      :rtype: pd.DataFrame



   .. py:method:: get_flightgroups(sort_by: str = None, ascending: bool = True) -> pandas.DataFrame

      Fetch Flight Groups data from the Airdata API based on query parameters.

      :param sort_by: Field to sort by. Valid values are 'title' and 'created'.
                      If None, no sorting is applied.
      :type sort_by: str, optional
      :param ascending: Whether to sort in ascending order. Defaults to True.
      :type ascending: bool
      :param id: Specific ID of a flight group to fetch.
      :type id: str, optional

      :returns:

                DataFrame containing retrieved flight data.
                    Returns empty DataFrame if request fails or no data found.
      :rtype: pd.DataFrame



   .. py:method:: get_flights(since: Optional[str] = None, until: Optional[str] = None, created_after: Optional[str] = None, battery_ids: Optional[Union[str, List[str]]] = None, pilot_ids: Optional[Union[str, List[str]]] = None, organizations: Optional[Union[str, List[str]]] = None, location: Optional[List[float]] = None, limit: int = 100, max_pages: int = 100, delay: float = 0.1, timeout: int = 15) -> pandas.DataFrame

      Retrieve paginated flight records from the Airdata API.

      Fetches flight data by automatically handling offset-based pagination across
      multiple API requests. Continues until no more results are returned or the
      maximum page limit is reached.

      :param since: Filter flights that started on or after this ISO 8601 timestamp
      :type since: str, optional
      :param until: Filter flights that started before this ISO 8601 timestamp.
      :type until: str, optional
      :param created_after: Include only flights created after this ISO 8601 timestamp.
      :type created_after: str, optional
      :param battery_ids: Filter by specific battery ID(s). Accepts either a comma-separated
                          string or a list of strings
      :type battery_ids: str or list, optional
      :param pilot_ids: Filter by specific pilot ID(s).
      :type pilot_ids: str or list, optional
      :param organizations: Filter flights by participant organization(s). Accepts either a
                            single organization name or a list of organization names. Only
                            flights with at least one participant belonging to one of the
                            specified organizations are returned.
      :type organizations: str or list, optional
      :param location: Geographic center point for radius-based search as
                       ``[latitude, longitude]``.
      :type location: list, optional
      :param limit: Number of records per page. Must be ≤ 100. Defaults to 100.
      :type limit: int, optional
      :param max_pages: Maximum number of pages to retrieve. Prevents excessive API usage.
                        Defaults to 100.
      :type max_pages: int, optional

      :returns:     A DataFrame containing all retrieved flight records with standardized
                    columns. Returns an empty DataFrame if:

                    - No flights match the query parameters
                    - API returns an error
                    - Authentication fails
      :rtype: pd.DataFrame

      :raises ValueError: If ``location`` is provided but doesn't contain exactly two numeric
          elements (latitude and longitude).



.. py:function:: get_flight_routes(df: pandas.DataFrame, filter_ids: Optional[List] = None, max_workers: int = 8, lon_col: str = 'longitude', lat_col: str = 'latitude', time_col: str = 'time(millisecond)', crs: str = 'EPSG:4326') -> geopandas.GeoDataFrame

   Extract flight routes from a DataFrame containing flight metadata and CSV URLs.

   This function processes each flight record in the input DataFrame, retrieves
   the associated CSV file containing flight data, and computes the flight route
   as a LineString geometry. It supports filtering by specific flight IDs and
   parallel processing for efficiency.

   :param df: DataFrame containing flight metadata, including a column
              named 'csvLink' with URLs to CSV files.
   :type df: pd.DataFrame
   :param filter_ids: List of flight IDs to process. If provided,
                      only flights with IDs in this list will be processed.
   :type filter_ids: list, optional
   :param max_workers: Number of parallel download threads.
   :type max_workers: int, optional
   :param lon_col: Column name for longitude.
   :type lon_col: str, optional
   :param lat_col: Column name for latitude.
   :type lat_col: str, optional
   :param time_col: Column name for timestamp.
   :type time_col: str, optional
   :param crs: Coordinate Reference System for the output GeoDataFrame.
   :type crs: str, optional

   :returns:

             A GeoDataFrame with one row per flight, containing the
                 flight metadata and a LineString geometry representing the flight route.
   :rtype: gpd.GeoDataFrame


.. py:function:: airPoint(*args, **kwargs)

.. py:function:: airLine(*args, **kwargs)

.. py:function:: airSegment(*args, **kwargs)

