from edmt.contrib.utils import (
    format_iso_time,
    append_cols,
    norm_exp
)
import logging
logger = logging.getLogger(__name__)

from typing import Union
import base64
import http.client
import json
import requests

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point

from io import StringIO
from tqdm import tqdm
from typing import Union, Optional

from pyproj import Geod
geod = Geod(ellps="WGS84")


class Airdata:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "api.airdata.com"
        self.authenticated = False
        self.auth_header = self._get_auth_header()

        self.authenticate(validate=True)

    def _get_auth_header(self):
        key_with_colon = self.api_key + ":"
        encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded_key}"
        }

    def authenticate(self,validate=True):
        """
        Authenticates with the API by calling /version or /flights.
        """
        conn = http.client.HTTPSConnection(self.base_url)
        payload = ''

        try:
            conn.request("GET", "/version", payload, self.auth_header)
            res = conn.getresponse()
            
            if res.status == 200:
                self.authenticated = True
                print("✅ Authentication successful.")
                return

            if res.status == 404:
                conn = http.client.HTTPSConnection(self.base_url)
                conn.request("GET", "/flights", payload, self.auth_header)
                res = conn.getresponse()

            if res.status == 200:
                self.authenticated = True
                print("✅ Authentication successful.")
            else:
                print(f"❌ Authentication failed. Status code: {res.status}")
                print(f"Response: {res.read().decode('utf-8')[:200]}")
                if validate:
                    raise ValueError("Authentication failed: Invalid API key or permissions.")

        except Exception as e:
            print(f"⚠️ Network error during authentication: {e}")
            if validate:
                raise

    def get_flights(
              self,since: str = None,until: str = None,limit: Union[int, None] = None,
              created_after: Optional[str] = None,battery_ids: Optional[Union[str, list]] = None,
              pilot_ids: Optional[Union[str, list]] = None,location: Optional[list] = None,
          ) -> pd.DataFrame:

          """
          Fetch flight data from the Airdata API based on the provided query parameters.

          Returns:
              pd.DataFrame: A DataFrame containing the retrieved flight data.
                          If the request fails or no data is found, returns an empty DataFrame.

          Raises:
              ValueError:
                  If `location` is not a list of exactly two numeric values (latitude and longitude).
          """

          if location is not None:
              if not isinstance(location, list) or len(location) != 2 or not all(isinstance(x, (int, float)) for x in location):
                  raise ValueError("Location must be a list of exactly two numbers: [latitude, longitude]")

          formatted_since = format_iso_time(since).replace("T", "+") if since else None
          formatted_until = format_iso_time(until).replace("T", "+") if until else None
          formatted_created_after = format_iso_time(created_after).replace("T", "+") if created_after else None

          params = {
              "start": formatted_since,
              "end": formatted_until,
              "detail_level": "comprehensive",
              "created_after": formatted_created_after,
              "battery_ids": ",".join(battery_ids) if battery_ids else None,
              "pilot_ids": ",".join(pilot_ids) if pilot_ids else None,
              "latitude": location[0] if location else None,
              "longitude": location[1] if location else None,
              "limit": limit
          }

          params = {k: v for k, v in params.items() if v is not None}

          endpoint = "/flights?" + "&".join([f"{k}={v}" for k, v in params.items()])
          
          if not self.authenticated:
              print("Cannot fetch flights: Not authenticated.")
              return None
                  
          try:
              conn = http.client.HTTPSConnection(self.base_url)
              conn.request("GET", endpoint, headers=self.auth_header)
              res = conn.getresponse()

              if res.status == 200:
                  data = json.loads(res.read().decode("utf-8"))
                  if "data" in data: 
                      normalized_data = list(tqdm(data["data"], desc="📥 Downloading"))
                      df = pd.json_normalize(normalized_data)
                      df = df.drop(
                          columns=[
                              "displayLink","kmlLink",
                              "gpxLink","originalLink",
                              "participants.object"
                          ],
                          errors='ignore'
                      )
                  else:
                    df = pd.DataFrame(data)
                  return df
              else:
                  print(f"Failed to fetch flights. Status code: {res.status}")
                  print(f"Response: {res.read().decode('utf-8')[:500]}")
                  return None
          except Exception as e:
              print(f"Error fetching flights: {e}")
              return None

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
                        normalized_data = list(tqdm(data, desc="📥 Downloading"))
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
    

def airPoint(df: pd.DataFrame, filter_ids: Optional[list] = None,log_errors: bool = True) -> gpd.GeoDataFrame:
    """
    Parameters:
        df (pd.DataFrame):
            A DataFrame containing at least two columns:
                - 'id': Unique identifier for each row.
                - 'csvLink': URL pointing to a CSV file.
        filter_ids (list or None):
            Optional list of IDs to restrict processing to specific rows.
        log_errors (bool):
            If True, prints errors encountered during CSV fetching or parsing. Defaults to True.
        expand_dict (bool):
            If True, expands dictionary fields like participants.data and batteries.data into separate columns.

    Returns:
        pd.DataFrame: A DataFrame combining metadata with CSV content.
                      Returns an empty DataFrame if no valid data was retrieved.

    Raises:
        ValueError:
            If required columns ('id', 'csvLink') are missing from the input DataFrame.
    """
    df = df.copy()
    df.loc[:, 'checktime'] = pd.to_datetime(df['time'], errors="coerce")

    required_cols = {'id', 'csvLink'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Input DataFrame must contain columns: {required_cols}")

    if filter_ids is not None:
        df = df[df['id'].isin(filter_ids)]

    all_combined_rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="🔄 Processing"):
        csv_url = row['csvLink']

        try:
            response = requests.get(csv_url)
            response.raise_for_status()
            csv_data = pd.read_csv(StringIO(response.text))
            metadata_repeated = pd.DataFrame([row] * len(csv_data), index=csv_data.index)
            combined = pd.concat([metadata_repeated, csv_data], axis=1)
            all_combined_rows.append(combined)

        except requests.RequestException as e:
            if log_errors:
                print(f"Network error for id {row['id']}: {e}")
        except pd.errors.ParserError as e:
            if log_errors:
                print(f"Parsing error for CSV at id {row['id']}: {e}")
        except Exception as e:
            if log_errors:
                print(f"Unexpected error for id {row['id']}: {e}")

    if not all_combined_rows:
        return pd.DataFrame()

    df_ = pd.concat(all_combined_rows, ignore_index=True)
    cols = ["participants.data", "batteries.data"]
    dfs_to_join = []
    for col in cols:
        try:
            expanded = pd.json_normalize(df_[col].explode(ignore_index=True))
            expanded.columns = [f"{col}_{subcol}" for subcol in expanded.columns]
            dfs_to_join.append(expanded)
        except Exception as e:
            if log_errors:
                print(f"Error expanding column '{col}': {e}")
    if dfs_to_join:
        expanded_df = pd.concat(dfs_to_join, axis=1)
    gdf = df_.join(expanded_df).drop(columns=cols)
    return append_cols(gdf,cols="checktime")


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
    gdf = gdf[gdf['geometry'] != Point(0, 0)]

    grouped = []
    for flight_id in tqdm(gdf['id'].unique(), desc="🔄 Processing flights"):
        flight_data = gdf[gdf['id'] == flight_id].sort_values(by='time(millisecond)')
        grouped.append(flight_data)

    gdf_sorted = pd.concat(grouped)

    def compute_distance(group):
        coords = [(p.x, p.y) for p in group.geometry.values]
        if len(coords) < 2:
            return None, None
        linestring = LineString(coords)
        total_distance = 0
        for i in range(len(coords) - 1):
            lon1, lat1 = coords[i]
            lon2, lat2 = coords[i + 1]
            _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
            total_distance += dist
        return linestring, total_distance

    results = []

    for flight_id, group in gdf_sorted.groupby('id'):
        linestring, distance = compute_distance(group)
        if linestring is not None:
            metadata = group.iloc[0].drop(['geometry', 'time(millisecond)']).to_dict()
            metadata['airline_time'] = group['time(millisecond)'].max()
            results.append({
                'id': flight_id,
                'geometry': linestring,
                'airline_distance_m': distance,
                **metadata
            })

    line_gdf = gpd.GeoDataFrame(results, geometry='geometry', crs="EPSG:4326")

    return append_cols(line_gdf, cols=['checktime','airline_time','airline_distance_m','geometry'])


def airSegment(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts a GeoDataFrame with point geometries into a GeoDataFrame with
    LineString segment geometries for each pair of consecutive points,
    grouped by 'id' and ordered by 'time(millisecond)'.

    Args:
        gdf: The input GeoDataFrame with 'id', 'time(millisecond)', and 'geometry'
             (Point) columns.

    Returns:
        A new GeoDataFrame where each row represents a line segment between two
        consecutive points.
    """
    segments = []

    gdf = gdf[gdf['geometry'] != Point(0, 0)]

    for flight_id in tqdm(gdf['id'].unique(), desc="🔄 Processing segments"):
        flight_data = gdf[gdf['id'] == flight_id].sort_values(by='time(millisecond)').reset_index(drop=True)

        for i in range(len(flight_data) - 1):
            pt1 = flight_data.loc[i, 'geometry']
            pt2 = flight_data.loc[i + 1, 'geometry']

            lon1, lat1 = pt1.x, pt1.y
            lon2, lat2 = pt2.x, pt2.y

            _, _, D_meters = geod.inv(lon1, lat1, lon2, lat2)
            t1 = flight_data.loc[i, 'time(millisecond)']
            t2 = flight_data.loc[i + 1, 'time(millisecond)']
            T = t2 - t1
            segment = LineString([pt1, pt2])

            attrs = flight_data.loc[i].drop(['geometry', 'time(millisecond)'])

            seg_dict = {
                'id': flight_id,
                'segment_start_time': t1,
                'segment_end_time': t2,
                'segment_duration_ms': T,
                'segment_distance_m': D_meters,
                'geometry': segment,
                **attrs.to_dict()
            }

            segments.append(seg_dict)

    if not segments:
        return gpd.GeoDataFrame(gdf,geometry='geometry')


    airSeg = gpd.GeoDataFrame(segments, geometry='geometry')

    return append_cols(airSeg, cols=['checktime','segment_start_time','segment_end_time','segment_duration_ms','segment_distance_m','geometry'])


