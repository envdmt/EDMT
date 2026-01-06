from edmt.contrib.utils import (
    format_iso_time,
    append_cols,
    norm_exp
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
from typing import List, Union, Optional
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



def _flight_to_polyline(
    row, 
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

    Raises:
        None — all exceptions are caught internally, and `None` is returned on failure.
    """
    try:
        url = row.get("csvLink")
        flight_id = row.get("id", "unknown")
        if not isinstance(url, str) or not url.startswith("http"):
            return None

        csv_df = AirdataCSV(row, max_retries=max_retries, timeout=timeout)

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
            "flight_distance_m": total_dist,
            "flight_time_max_ms": pts[time_col].max()
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

        lon_col (str, optional): Column name for longitude in the CSV files.
        lat_col (str, optional): Column name for latitude in the CSV files.
        time_col (str, optional): Column name for timestamp in the CSV files.
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
            executor.submit(_flight_to_polyline, row, lon_col, lat_col, time_col): idx
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