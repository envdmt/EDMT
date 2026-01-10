from edmt.contrib.utils import (
    format_iso_time,
    append_cols,
    norm_exp
)
from edmt.base.base import (
    AirdataBaseClass,
    ExtractCSV
)

import logging
logger = logging.getLogger(__name__)

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import duckdb
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import LineString, Point
from tqdm.auto import tqdm
from typing import List, Union, Optional
import http.client
from pyproj import Geod
geod = Geod(ellps="WGS84")


class Airdata(AirdataBaseClass):
    """
    Client for interacting with the Airdata API.
    Handles authentication and provides methods to fetch various data types
    such as flights,flight groups, drones, batteries, and pilots.
    """
    
    def AccessGroups(self, endpoint: str) -> Optional[pd.DataFrame]:
      if not self.authenticated:
        logger.warning(f"Cannot fetch {endpoint}: Not authenticated.")
        return None

      try:
        conn = http.client.HTTPSConnection(self.base_url)
        conn.request("GET", endpoint, headers=self._get_auth_header())
        res = conn.getresponse()

        if res.status == 200:
            data = json.loads(res.read().decode("utf-8"))
            if "data" in data:
                normalized_data = list(tqdm(data["data"], desc="📥 Downloading"))
                normalized = pd.json_normalize(normalized_data)
                df = norm_exp(normalized,"flights.data")
            else:
                df = pd.DataFrame(data)
            return df
        else:
            logger.warning(f"Failed to fetch flights. Status code: {res.status}")
            logger.warning(f"Response: {res.read().decode('utf-8')[:500]}")
            return None
      except Exception as e:
          logger.warning(f"Error fetching flights: {e}")
          return None
      finally:
          if 'conn' in locals() and conn:
              conn.close()

    def AccessItems(self, endpoint: str) -> Optional[pd.DataFrame]:
        """
        Sends a GET request to the specified API endpoint and returns normalized data as a DataFrame.

        Parameters:
            endpoint (str): The full API path including query parameters.

        Returns:
            Optional[pd.DataFrame]: A DataFrame containing the retrieved data, or None if the request fails.
        """
        if not self.authenticated:
            logger.warning("Cannot fetch data: Not authenticated.")
            return None

        try:
            conn = http.client.HTTPSConnection(self.base_url)
            try:
                conn.request("GET", f"/{endpoint}", headers=self.auth_header)
                res = conn.getresponse()
                if res.status == 200:
                    raw_data = res.read().decode("utf-8")
                    try:
                        data = json.loads(raw_data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to decode JSON response: {e}")
                        return None

                    if isinstance(data, list):
                        normalized_data = list(tqdm(data, desc="Downloading"))
                    else:
                        logger.info("Response data is not a list; returning raw.")
                        normalized_data = data

                    if not isinstance(normalized_data, (list, dict)):
                        logger.warning("Data is not a valid type for json_normalize.")
                        return None

                    df = pd.json_normalize(normalized_data)
                    return df
                else:
                    logger.warning(f"Failed to fetch '{endpoint}'.")
                    return None
            finally:
                conn.close()

        except Exception as e:
            logger.warning(f"Network error while fetching '{endpoint}': {e}")
            return None
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    def get_drones(self) -> pd.DataFrame:
        """
        Fetch drone data from the Airdata API based on the provided query parameters.


        Returns:
            pd.DataFrame: A DataFrame containing the retrieved flight data. 
                        If the request fails or no data is found, returns an empty DataFrame.
        """

        df = self.AccessItems(endpoint="drones")
        return df if df is not None else pd.DataFrame()
        
    def get_batteries(self) -> pd.DataFrame:
        """
        Fetch batteries data from the Airdata API based on the provided query parameters.


        Returns:
            pd.DataFrame: A DataFrame containing the retrieved flight data. 
                        If the request fails or no data is found, returns an empty DataFrame.
        """
        df = self.AccessItems(endpoint="batteries")
        return df if df is not None else pd.DataFrame()
    
    def get_pilots(self) -> pd.DataFrame:
        """
        Fetch pilots data from the Airdata API based on the provided query parameters.


        Returns:
            pd.DataFrame: A DataFrame containing the retrieved flight data. 
                        If the request fails or no data is found, returns an empty DataFrame.
        """

        df = self.AccessItems(endpoint="pilots")
        return df if df is not None else pd.DataFrame()

    def get_flightgroups(
        self,
        sort_by: str = None,
        ascending: bool = True
    ) -> pd.DataFrame:
        """
        Fetch Flight Groups data from the Airdata API based on query parameters.

        Parameters:
            sort_by (str, optional): Field to sort by. Valid values are 'title' and 'created'.
                                     If None, no sorting is applied.
            ascending (bool): Whether to sort in ascending order. Defaults to True.
            id (str, optional): Specific ID of a flight group to fetch.

        Returns:
            pd.DataFrame: DataFrame containing retrieved flight data.
                          Returns empty DataFrame if request fails or no data found.
        """
        params = {}
        if sort_by:
            if sort_by not in ["title", "created"]:
                raise ValueError("Invalid sort_by value. Must be 'title' or 'created'.")
            params["sort_by"] = sort_by
            params["sort_dir"] = "asc" if ascending else "desc"
        endpoint = "/flightgroups?" + "&".join([f"{k}={v}" for k, v in params.items()])

        df = self.AccessGroups(endpoint=endpoint)
        return df if df is not None else pd.DataFrame()

    def get_flights(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        created_after: Optional[str] = None,
        battery_ids: Optional[Union[str, List[str]]] = None,
        pilot_ids: Optional[Union[str, List[str]]] = None,
        location: Optional[List[float]] = None,
        limit: int = 100,
        max_pages: int = 100,
        delay: float = 0.1,
        timeout: int = 15,
    ) -> pd.DataFrame:
        """Retrieve paginated flight records from the Airdata API.

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
        """
        if not self.authenticated:
            logger.error("Cannot fetch flights: Not authenticated.")
            return pd.DataFrame()

        if location is not None:
            if not (isinstance(location, list) and len(location) == 2 and all(isinstance(x, (int, float)) for x in location)):
                raise ValueError("Location must be a list of exactly two numbers: [latitude, longitude]")

        def format_for_api(dt_str):
            return format_iso_time(dt_str).replace("T", "+") if dt_str else None

        params = {
            "start": format_for_api(since),
            "end": format_for_api(until),
            "created_after": format_for_api(created_after),
            "detail_level": "comprehensive",
            "battery_ids": ",".join(battery_ids) if isinstance(battery_ids, list) else battery_ids,
            "pilot_ids": ",".join(pilot_ids) if isinstance(pilot_ids, list) else pilot_ids,
            "latitude": location[0] if location else None,
            "longitude": location[1] if location else None,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}

        all_data = []
        offset = 0

        with tqdm(desc="Downloading flights") as pbar:
            for page in range(max_pages):
                current_params = {**params, "offset": offset}
                query_string = "&".join(f"{k}={v}" for k, v in current_params.items())
                endpoint = f"/flights?{query_string}"

                try:
                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("GET", endpoint, headers=self.auth_header)
                    res = conn.getresponse()

                    if res.status != 200:
                        error_msg = res.read().decode('utf-8')[:300]
                        logger.error(f"HTTP {res.status}: {error_msg}")
                        break

                    data = json.loads(res.read().decode("utf-8"))
                    if not data.get("data") or len(data["data"]) == 0:
                        break

                    normalized_data = data["data"]
                    df_page = pd.json_normalize(normalized_data)

                    all_data.append(df_page)
                    fetched_this_page = len(normalized_data)

                    for _ in range(fetched_this_page):
                        pbar.update(1)

                    offset += limit
                    page += 1
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error on page {page + 1} at offset {offset}: {e}")
                    break

        if not all_data:
            logger.info("No flight data found.")
            return pd.DataFrame()

        df = pd.concat(all_data, ignore_index=True)
        if "time" in df.columns:
            df["checktime"] = pd.to_datetime(df["time"], errors="coerce").dt.tz_localize(None)
        return append_cols(df, cols="checktime")


def _flight_polyline(
    row,
    link_col="csvLink",
    lon_col="longitude", 
    lat_col="latitude", 
    time_col="time(millisecond)",
    max_retries=3, 
    timeout=15
    ):
    """
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

    """
    try:
        url = row[link_col]
        flight_id = row.get("id", "unknown")
        if not isinstance(url, str) or not url.startswith("http"):
            return None

        csv_df = ExtractCSV(row, col=link_col,max_retries=max_retries, timeout=timeout)

        required_cols = [lon_col, lat_col, time_col]
        if not all(col in csv_df.columns for col in required_cols):
            logger.warning(f"Flight {flight_id}: missing required columns")
            return None

        valid = (csv_df[lon_col] != 0) & (csv_df[lat_col] != 0)
        pts = csv_df[valid].copy()
        if len(pts) < 2:
            return None

        pts[time_col] = pd.to_numeric(pts[time_col], errors="coerce")
        pts = pts.dropna(subset=[time_col]).sort_values(by=time_col)

        if len(pts) < 2:
            return None

        coords = list(zip(pts[lon_col], pts[lat_col]))
        line = LineString(coords)

        total_dist = 0.0
        for i in range(len(coords) - 1):
            try:
                _, _, d = geod.inv(*coords[i], *coords[i + 1])
                total_dist += abs(d)
            except Exception:
                continue

        meta = row.drop(["csvLink"]).to_dict()
        meta.update({
            "id": flight_id,
            "geometry": line,
            "airline_distance_m": total_dist,
            "airline_time": pts[time_col].max()
        })
        return meta

    except Exception as e:
        return None
    

def get_flight_routes(
    df: pd.DataFrame,
    filter_ids: Optional[List] = None,
    max_workers: int = 8,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    time_col: str = "time(millisecond)",
    crs: str = "EPSG:4326"
) -> gpd.GeoDataFrame:
    """
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
    """

    required = {"id", "csvLink"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing required columns: {required}")

    df = df.copy()
    if filter_ids:
        df = df[df["id"].isin(filter_ids)].reset_index(drop=True)

    if df.empty:
        return gpd.GeoDataFrame()

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _flight_polyline,
                row,
                link_col="csvLink",
                lon_col=lon_col,
                lat_col=lat_col,
                time_col=time_col,
                max_retries=3,
                timeout=15
            ): idx
            for idx, row in df.iterrows()
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing"):
            res = future.result()
            if res is not None:
                results.append(res)

    if not results:
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(results, geometry="geometry", crs=crs)
    return gdf


def airPoint(
    df: pd.DataFrame,
    filter_ids: Optional[List] = None,
    link_col: str = "csvLink",
    max_retries: int = 3,
    timeout: int = 10,
    chunk_size: int = 100,
    max_workers: int = 20,
) -> gpd.GeoDataFrame:
    """
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
    """

    if len(df) > 500:
        print("Large dataset detected. Use get_flight_routes. to get better performance and convert to Line Geometries.")
        return gpd.GeoDataFrame()

    if link_col not in df.columns:
        raise ValueError(f"Column '{link_col}' not found in DataFrame.")
    if "id" not in df.columns:
        raise ValueError("Column 'id' is required.")

    df = df.copy()
    df["checktime"] = pd.to_datetime(df["time"], errors="coerce")

    if filter_ids is not None:
        df = df[df["id"].isin(filter_ids)]

    if df.empty:
        return gpd.GeoDataFrame()

    total_rows = len(df)
    use_chunks = total_rows > chunk_size
    chunk_starts = list(range(0, total_rows, chunk_size)) if use_chunks else [0]

    all_results = []

    outer_pbar = tqdm(
        total=total_rows,
        desc="Processing flights",
        position=0,
        leave=True,
    )

    for chunk_num, start_idx in enumerate(chunk_starts):
        chunk_df = df.iloc[start_idx : start_idx + chunk_size].reset_index(drop=True)

        inner_pbar = tqdm(
            total=len(chunk_df),
            desc=f"Chunk {chunk_num + 1}/{len(chunk_starts)}",
            position=1,
            leave=False,
        ) if use_chunks else None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_row = {
                executor.submit(
                    ExtractCSV,
                    row,
                    col=link_col,
                    max_retries=max_retries,
                    timeout=timeout,
                ): row
                for _, row in chunk_df.iterrows()
            }

            for future in as_completed(future_to_row):
                telemetry_df = future.result()
                source_row = future_to_row[future]

                if telemetry_df is not None and not telemetry_df.empty:
                    metadata_repeated = pd.DataFrame(
                        [source_row] * len(telemetry_df),
                        index=telemetry_df.index,
                    )
                    merged = pd.concat(
                        [metadata_repeated.reset_index(drop=True),
                         telemetry_df.reset_index(drop=True)],
                        axis=1,
                    )
                    all_results.append(merged)

                outer_pbar.update(1)
                if inner_pbar:
                    inner_pbar.update(1)

        if inner_pbar:
            inner_pbar.close()

    outer_pbar.close()

    if not all_results:
        return gpd.GeoDataFrame()

    combined = pd.concat(all_results, ignore_index=True)

    if {"longitude", "latitude"}.issubset(combined.columns):
        gdf = gpd.GeoDataFrame(
            combined,
            geometry=gpd.points_from_xy(
                combined.longitude.astype(float),
                combined.latitude.astype(float),
            ),
            crs="EPSG:4326",
        )
    else:
        raise ValueError(
            "Expected 'longitude' and 'latitude' columns for GeoDataFrame creation"
        )

    return gdf


def airLine(
    gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
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
    """
    gdf = gdf[gdf['geometry'] != Point(0, 0)].copy()

    if gdf.empty:
        return gpd.GeoDataFrame()

    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    gdf['lon'] = gdf.geometry.x
    gdf['lat'] = gdf.geometry.y

    df = pd.DataFrame(gdf.drop(columns='geometry'))

    con = duckdb.connect(':memory:')
    con.register('df', df)

    query = """
        SELECT *
        FROM df
        ORDER BY id, "time(millisecond)"
    """
    sorted_df = con.execute(query).df()
    con.close()

    grouped = sorted_df.groupby('id', sort=False)

    results = []

    for flight_id, group in tqdm(grouped, desc="Processing"):
        coords = list(zip(group['lon'].values, group['lat'].values))
        if len(coords) < 2:
            continue

        linestring = LineString(coords)

        total_distance = 0.0
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
            total_distance += dist

        first_row = group.iloc[0].drop(['lon', 'lat', 'time(millisecond)']).to_dict()
        first_row.update({
            'id': flight_id,
            'geometry': linestring,
            'airline_distance_m': total_distance,
            'airline_time': group['time(millisecond)'].max()
        })
        results.append(first_row)

    if not results:
        return gpd.GeoDataFrame()

    line_gdf = gpd.GeoDataFrame(results, geometry='geometry', crs="EPSG:4326")
    return append_cols(line_gdf, cols=['checktime','airline_time','airline_distance_m','geometry'])


def airSegment(
    gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
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
    """

    if gdf.empty:
        return gpd.GeoDataFrame()

    gdf = gdf[gdf['geometry'] != Point(0, 0)].copy()
    if gdf.empty:
        return gpd.GeoDataFrame()

    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    df = gdf.copy()
    df['lon'] = df.geometry.x
    df['lat'] = df.geometry.y
    df = df.drop(columns='geometry')

    con = duckdb.connect(':memory:')
    con.register('df', df)
    sorted_df = con.execute("""
        SELECT *,
               LEAD("time(millisecond)") OVER (PARTITION BY id ORDER BY "time(millisecond)") AS next_time,
               LEAD(lon) OVER (PARTITION BY id ORDER BY "time(millisecond)") AS next_lon,
               LEAD(lat) OVER (PARTITION BY id ORDER BY "time(millisecond)") AS next_lat
        FROM df
    """).df()
    con.close()

    seg_df = sorted_df.dropna(subset=['next_time']).copy()
    seg_df['next_time'] = seg_df['next_time'].astype(np.int64)

    total_segments = len(seg_df)
    if total_segments == 0:
        return gpd.GeoDataFrame()

    geometries = []
    desc = "Processing segments"
    for _, row in tqdm(seg_df[['lon', 'lat', 'next_lon', 'next_lat']].iterrows(),
                       total=total_segments, desc=desc, unit="seg"):
        geom = LineString([(row['lon'], row['lat']), (row['next_lon'], row['next_lat'])])
        geometries.append(geom)
    seg_df['geometry'] = geometries

    lon1 = seg_df['lon'].values
    lat1 = seg_df['lat'].values
    lon2 = seg_df['next_lon'].values
    lat2 = seg_df['next_lat'].values
    _, _, dists = geod.inv(lon1, lat1, lon2, lat2)
    seg_df['segment_distance_m'] = dists

    seg_df['segment_start_time'] = seg_df['time(millisecond)']
    seg_df['segment_end_time'] = seg_df['next_time']
    seg_df['segment_duration_ms'] = seg_df['next_time'] - seg_df['time(millisecond)']

    drop_cols = {'lon', 'lat', 'next_lon', 'next_lat', 'next_time'}
    meta_cols = [c for c in seg_df.columns if c not in drop_cols]
    seg_gdf = gpd.GeoDataFrame(seg_df[meta_cols], geometry='geometry', crs="EPSG:4326")

    required_cols = ['checktime', 'segment_start_time', 'segment_end_time',
                     'segment_duration_ms', 'segment_distance_m', 'geometry']
    
    return append_cols(seg_gdf,cols=required_cols)

