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


def _process_flight_to_polyline(row, lon_col="longitude", lat_col="latitude", time_col="time(millisecond)"):
    """
    Process a single flight row:
    - Download CSV from csvLink
    - Clean points (remove 0,0)
    - Build LineString
    - Compute geodesic distance
    - Return flight metadata + geometry
    """
    try:
        url = row.get("csvLink")
        flight_id = row.get("id", "unknown")
        if not isinstance(url, str) or not url.startswith("http"):
            return None

        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        csv_df = pd.read_csv(StringIO(resp.text), low_memory=False)

        if csv_df.empty:
            return None

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