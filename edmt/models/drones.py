from edmt.contrib.utils import (
    format_iso_time,
    append_cols,
    norm_exp,
    dict_expand
)
from edmt.base.base import (
    AirdataBaseClass,
    AirdataCSV
)

import logging
logger = logging.getLogger(__name__)

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
from tqdm.auto import tqdm
from typing import Union, Optional
import http.client
from pyproj import Geod
geod = Geod(ellps="WGS84")


class Airdata(AirdataBaseClass):
    """
    Client for interacting with the Airdata API.
    Handles authentication and provides methods to fetch various data types
    such as flights, drones, batteries, and pilots.
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
    
    def get_flights(
        self,
        since: str = None,
        until: str = None,
        created_after: Optional[str] = None,
        battery_ids: Optional[Union[str, list]] = None,
        pilot_ids: Optional[Union[str, list]] = None,
        location: Optional[list] = None,
        limit: int = 100,
        max_pages: int = 100,
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

        if location is not None:
            if not isinstance(location, list) or len(location) != 2 or not all(isinstance(x, (int, float)) for x in location):
                raise ValueError("Location must be a list of exactly two numbers: [latitude, longitude]")

        def format_for_api(dt_str):
            return format_iso_time(dt_str).replace("T", "+") if dt_str else None

        formatted_since = format_for_api(since)
        formatted_until = format_for_api(until)
        formatted_created_after = format_for_api(created_after)

        params = {
            "start": formatted_since,
            "end": formatted_until,
            "detail_level": "comprehensive",
            "created_after": formatted_created_after,
            "battery_ids": ",".join(battery_ids) if isinstance(battery_ids, list) else battery_ids,
            "pilot_ids": ",".join(pilot_ids) if isinstance(pilot_ids, list) else pilot_ids,
            "latitude": location[0] if location else None,
            "longitude": location[1] if location else None,
            "limit": limit,
        }

        params = {k: v for k, v in params.items() if v is not None}

        if not self.authenticated:
            print("Cannot fetch flights: Not authenticated.")
            return pd.DataFrame()

        all_data = []
        offset = 0
        page = 0

        with tqdm(desc="Downloading flights") as pbar:
            while page < max_pages:
                current_params = params.copy()
                current_params["offset"] = offset

                query_string = "&".join([f"{k}={v}" for k, v in current_params.items()])
                endpoint = f"/flights?{query_string}"

                try:
                    conn = http.client.HTTPSConnection(self.base_url)
                    conn.request("GET", endpoint, headers=self.auth_header)
                    res = conn.getresponse()

                    if res.status != 200:
                        error_msg = res.read().decode('utf-8')[:300]
                        print(f"HTTP {res.status}: {error_msg}")
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
                    print(f"Error on page {page + 1} at offset {offset}: {e}")
                    break

        if not all_data:
            print("No flight data found.")
            return pd.DataFrame()

        df = pd.concat(all_data, ignore_index=True)
        df["checktime"] = pd.to_datetime(df["time"], errors="coerce").dt.tz_localize(None)
        return append_cols(df,cols="checktime")

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


def df_to_gdf( df: pd.DataFrame,lon_col: str = 'longitude',lat_col: str = 'latitude',crs: int = 4326) -> gpd.GeoDataFrame:
    """
    Convert a pandas DataFrame with latitude and longitude columns into a GeoDataFrame
    with point geometries.

    Parameters:
        df (pd.DataFrame):
            Input DataFrame containing geographic coordinates.
        lon_col (str):
            Name of the column in `df` that contains longitude values. Default is `'longitude'`.
        lat_col (str):
            Name of the column in `df` that contains latitude values. Default is `'latitude'`.
        crs (int):
            Coordinate Reference System (CRS) to assign to the resulting GeoDataFrame.
            Defaults to 4326 (WGS84 - standard latitude/longitude).

    Returns:
        gpd.GeoDataFrame:
            A GeoDataFrame with point geometries created from the latitude and longitude columns.
            The original DataFrame columns are preserved.

    Raises:
        KeyError:
            If either of the specified latitude or longitude columns is not present in the DataFrame.
        ValueError:
            If the CRS is invalid or not supported by GeoPandas.
    """
    if lat_col not in df.columns or lon_col not in df.columns:
        missing = [col for col in [lat_col, lon_col] if col not in df.columns]
        raise KeyError(f"Missing required column(s): {missing}")

    try:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
            crs=crs
        )
    except Exception as e:
        raise ValueError(f"Failed to create GeoDataFrame: {e}")

    return gdf


def airPoint(df: pd.DataFrame, filter_ids: Optional[list] = None) -> pd.DataFrame:
    """
    Downloads and processes CSV data from URLs in a metadata DataFrame, optionally filtered by ID.

    Args:
        df (pd.DataFrame): 
            Input metadata DataFrame containing at least:
                - 'id': Unique identifier for each record.
                - 'csvLink': Valid URL string pointing to a downloadable CSV file.
        filter_ids (list, optional): 
            If provided, only rows with 'id' values in this list will be processed.
            Defaults to None (process all rows).

    Returns:
        pd.DataFrame: 
            A combined DataFrame where each row from each downloaded CSV is annotated
            with its source metadata (e.g., 'id', 'csvLink', etc.), and structured
            dictionary fields (like 'participants.data') are expanded into flat columns.
            Returns an empty DataFrame if no valid CSV data could be retrieved.

    Raises:
        ValueError: 
            If the required column 'csvLink' is missing from the input DataFrame.

    """

    chunk_size=200 # Process rows in chunks if len(df) > chunk_size (default: 200).
    max_workers=20 # Number of parallel threads for downloading (default: 20).
    retries=3 # Number of retry attempts per URL (default: 3).
    timeout=10 # Timeout for each HTTP request in seconds (default: 10).
    cols = ["participants.data", "batteries.data"]

    df = df.copy()
    df["checktime"] = pd.to_datetime(df["time"], errors="coerce")

    if filter_ids is not None:
        df = df[df["id"].isin(filter_ids)]

    if df.empty:
        return pd.DataFrame()

    if "csvLink" not in df.columns:
        raise ValueError(f"Column 'csvLink' not found in DataFrame.")
    
    total_rows = len(df)
    use_chunks = total_rows > chunk_size
    all_dfs = []

    if use_chunks:
        iterable = range(0, total_rows, chunk_size)
        total_chunks = len(iterable)
        chunk_iter = tqdm(iterable, desc="Processing", total=total_chunks)
    else:
        chunk_iter = [0]
        total_chunks = 1

    for start_idx in chunk_iter:
        if use_chunks:
            chunk_df = df.iloc[start_idx:start_idx + chunk_size].reset_index(drop=True)
        else:
            chunk_df = df.reset_index(drop=True)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(AirdataCSV, row, retries, timeout): idx
                for idx, row in chunk_df.iterrows()
            }
            chunk_pbar = tqdm(
                total=len(future_to_idx),
                desc=f"Chunk {start_idx // chunk_size + 1}/{total_chunks}" if use_chunks else "Processing",
                leave=not use_chunks
            )

            for future in as_completed(future_to_idx):
                result = future.result()
                if result is not None:
                    all_dfs.append(result)
                chunk_pbar.update(1)
            chunk_pbar.close()

    if not all_dfs:
        return pd.DataFrame()

    df_ = pd.concat(all_dfs, ignore_index=True)
    df = dict_expand(df_,cols)
    return append_cols(df,cols="checktime")


def airLine(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts a GeoDataFrame with point geometries into a GeoDataFrame with
    LineString geometries for each unique 'id', ordered by 'time(millisecond)'.

    Adds a new column 'distance_m' representing the total geodesic length of the line.

    Args:
        gdf: The input GeoDataFrame with 'id', 'time(millisecond)', and 'geometry'
            (Point) columns.

    Returns:
        A new GeoDataFrame where each row represents a unique 'id' and its
        corresponding LineString geometry and total distance in meters.
    """
    mask = ~((gdf.geometry.x == 0) & (gdf.geometry.y == 0))
    gdf = gdf[mask].copy()

    if gdf.empty:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    id_col = 'id'
    time_col = 'time(millisecond)'
    gdf = gdf.sort_values([id_col, time_col]).reset_index(drop=True)

    gdf['_x'] = gdf.geometry.x
    gdf['_y'] = gdf.geometry.y

    results = []
    groups = gdf.groupby(id_col, sort=False)

    for flight_id, group in tqdm(groups, desc="Processing flights", total=groups.ngroups):
        if len(group) < 2:
            continue

        coords = group[['_x', '_y']].values
        linestring = LineString(coords)

        lons1 = coords[:-1, 0]
        lats1 = coords[:-1, 1]
        lons2 = coords[1:, 0]
        lats2 = coords[1:, 1]

        _, _, dists = geod.inv(lons1, lats1, lons2, lats2)
        total_distance = np.sum(dists)

        first_row = group.iloc[0]
        metadata = {
            col: first_row[col]
            for col in group.columns
            if col not in {'geometry', time_col, '_x', '_y'}
        }

        metadata.update({
            'id': flight_id,
            'geometry': linestring,
            'airline_time': group[time_col].max(),
            'airline_distance_m': total_distance
        })
        results.append(metadata)

    if not results:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    line_gdf = gpd.GeoDataFrame(results, geometry='geometry', crs="EPSG:4326")

    return append_cols(line_gdf, cols=['checktime','airline_time','airline_distance_m','geometry'])


def airSegment(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    The function is optimized for large datasets using vectorized operations and avoids
    slow per-row loops.

    Args:
        gdf (geopandas.GeoDataFrame): 
            Input trajectory data with the following required columns:
            - `id`: Unique track identifier (e.g., flight ID)
            - `time(millisecond)`: Numeric timestamp in milliseconds
            - `segment_duration_ms`: Time difference between points (ms)
            - `segment_distance_m`: Geodesic distance between points (meters)
            - Original metadata columns (copied from the *starting* point of each segment)
            
            The output retains the original CRS (assumed to be EPSG:4326) and uses
            LineString geometries. Returns an empty GeoDataFrame if no valid segments
            can be formed.
    """
    if gdf.empty:
        return gpd.GeoDataFrame(geometry=[], crs=gdf.crs or "EPSG:4326")

    mask = ~((gdf.geometry.x == 0) & (gdf.geometry.y == 0))
    gdf = gdf[mask].copy()

    if gdf.empty:
        return gpd.GeoDataFrame(geometry=[], crs=gdf.crs)

    gdf = gdf.sort_values(['id', 'time(millisecond)']).reset_index(drop=True)

    gdf['_x'] = gdf.geometry.x
    gdf['_y'] = gdf.geometry.y

    all_segments = []
    grouped = gdf.groupby('id', sort=False)

    for flight_id, group in tqdm(grouped, desc="Processing segments", total=grouped.ngroups):
        n = len(group)
        if n < 2:
            continue

        coords = group[['_x', '_y']].values
        starts = coords[:-1]
        ends = coords[1:]

        lons1, lats1 = starts[:, 0], starts[:, 1]
        lons2, lats2 = ends[:, 0], ends[:, 1]
        _, _, dists = geod.inv(lons1, lats1, lons2, lats2)

        times = group['time(millisecond)'].values
        t1s = times[:-1]
        t2s = times[1:]
        durations = t2s - t1s

        geometries = [
            LineString([(x1, y1), (x2, y2)])
            for (x1, y1), (x2, y2) in zip(starts, ends)
        ]

        base_attrs = group.drop(columns=['geometry', 'time(millisecond)', '_x', '_y']).iloc[:-1].reset_index(drop=True)

        seg_df = pd.DataFrame({
            'id': flight_id,
            'segment_start_time': t1s,
            'segment_end_time': t2s,
            'segment_duration_ms': durations,
            'segment_distance_m': dists,
            'geometry': geometries
        })

        combined = pd.concat([seg_df, base_attrs], axis=1)
        all_segments.append(combined)

    if not all_segments:
        return gpd.GeoDataFrame(geometry=[], crs=gdf.crs)

    result = pd.concat(all_segments, ignore_index=True)
    segment_gdf = gpd.GeoDataFrame(result, geometry='geometry', crs=gdf.crs)

    return append_cols(
        segment_gdf,
        cols=['checktime', 'segment_start_time', 'segment_end_time',
              'segment_duration_ms', 'segment_distance_m', 'geometry']
    )

