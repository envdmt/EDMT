import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from pyproj import Geod
import requests
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm.auto import tqdm
from typing import Optional, List
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
geod = Geod(ellps="WGS84")


def _process_flight_to_polyline(
    row,
    url_col="csvLink",
    id_col="id",
    lon_col="longitude",
    lat_col="latitude",
    time_col="time(millisecond)",
    max_retries=3,
    timeout=15,
    logger=None
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
        if hasattr(row, 'to_dict'):
            row_dict = row.to_dict()
        elif isinstance(row, dict):
            row_dict = row.copy()
        else:
            logger.error("Row must be a dict or pandas Series")
            return None

        url = row_dict.get(url_col)
        flight_id = row_dict.get(id_col, "unknown")

        # Validate URL
        if not isinstance(url, str) or not url.strip().startswith(("http://", "https://")):
            logger.warning(f"Flight {flight_id}: invalid or missing URL in '{url_col}'")
            return None

        # Temporarily inject URL into a dummy row for AirdataCSV (which expects a dict/Series with col key)
        dummy_row = {url_col: url}
        csv_df = AirdataCSV(dummy_row, col=url_col, max_retries=max_retries, timeout=timeout)

        if csv_df is None:
            logger.warning(f"Flight {flight_id}: failed to download or parse CSV after retries")
            return None

        # Validate required columns
        required_cols = [lon_col, lat_col, time_col]
        if not all(col in csv_df.columns for col in required_cols):
            logger.warning(f"Flight {flight_id}: missing one or more required columns: {required_cols}")
            return None

        # Remove invalid (0,0) coordinates
        valid = (csv_df[lon_col] != 0) & (csv_df[lat_col] != 0)
        pts = csv_df[valid].copy()
        if len(pts) < 2:
            logger.debug(f"Flight {flight_id}: fewer than 2 valid points after removing (0,0)")
            return None

        # Ensure time column is numeric and clean
        pts[time_col] = pd.to_numeric(pts[time_col], errors="coerce")
        pts = pts.dropna(subset=[time_col]).sort_values(by=time_col).reset_index(drop=True)

        if len(pts) < 2:
            logger.debug(f"Flight {flight_id}: fewer than 2 points after time cleaning")
            return None

        # Build coordinate list
        coords = list(zip(pts[lon_col], pts[lat_col]))

        # Compute total geodesic distance
        total_dist = 0.0
        for i in range(len(coords) - 1):
            try:
                _, _, dist = geod.inv(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1])
                total_dist += abs(dist)
            except Exception:
                # Skip segment on geodetic error (e.g., antipodal, invalid coord)
                continue

        meta = {k: v for k, v in row_dict.items() if k != url_col}
        meta.update({
            id_col: flight_id,
            "geometry": LineString(coords),
            "flight_distance_m": total_dist,
            "flight_time_max_ms": pts[time_col].max()
        })

        return meta

    except Exception as e:
        logger.debug(f"Failed processing flight {row.get('id', 'N/A')}: {e}")
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
    Parallel, memory-efficient pipeline to convert drone flights → polylines.

    Parameters:
        df: Must contain 'id' and 'csvLink'
        filter_ids: Optional list of flight IDs to process
        max_workers: Number of parallel download threads
        lon_col/lat_col/time_col: Expected column names in CSV
        crs: Output CRS (default WGS84)

    Returns:
        gpd.GeoDataFrame: One row per flight, geometry = LineString
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
            executor.submit(_process_flight_to_polyline, row, lon_col, lat_col, time_col): idx
            for idx, row in df.iterrows()
        }

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing flights"):
            res = future.result()
            if res is not None:
                results.append(res)

    if not results:
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(results, geometry="geometry", crs=crs)
    return gdf