from edmt.contrib.utils import (
    format_iso_time,
    append_cols
)

from typing import Union
import base64
import http.client
import json
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString, Point
import requests
from io import StringIO
from tqdm import tqdm
from typing import Union, Optional

def example(created_after: Optional[str] = None):
    print(created_after)


class Airdata:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "api.airdata.com"
        self.authenticated = False
        self.auth_header = self._get_auth_header()

        # Automatically authenticate on instantiation
        self.authenticate(validate=True)

    def _get_auth_header(self):
        """
        Manually constructs the Basic Auth header.
        Returns a properly encoded Authorization header dict.
        """
        key_with_colon = self.api_key + ":"
        encoded_key = base64.b64encode(key_with_colon.encode()).decode("utf-8")
        return {
            "Authorization": f"Basic {encoded_key}"
        }

    def authenticate(
        self, 
        validate=True
        ):
        """
        Authenticates with the Airdata API by calling /version or /flights.
        Sets self.authenticated = True if successful.
        """
        conn = http.client.HTTPSConnection(self.base_url)
        payload = ''

        try:
            conn.request("GET", "/version", payload, self.auth_header)
            res = conn.getresponse()
            
            if res.status == 200:
                self.authenticated = True
                print("Authentication successful.")
                return

            # If /version not found, try /flights as fallback
            if res.status == 404:
                print("/version endpoint not found. Trying /flights...")
                conn = http.client.HTTPSConnection(self.base_url)
                conn.request("GET", "/flights", payload, self.auth_header)
                res = conn.getresponse()

            if res.status == 200:
                self.authenticated = True
                print("Authentication successful using /flights.")
            else:
                print(f"Authentication failed. Status code: {res.status}")
                print(f"Response: {res.read().decode('utf-8')[:200]}")
                if validate:
                    raise ValueError("Authentication failed: Invalid API key or permissions.")

        except Exception as e:
            print(f"⚠️ Network error during authentication: {e}")
            if validate:
                raise

    def get_flights(
        self,
        since: str,
        until: str,
        limit: Union[int, None] = None,
        created_after: Optional[str] = None,
        battery_ids: list | None = None,
        pilot_ids: list | None = None,
        location: list | None = None,  # Should be [lat, lon]
        ) -> pd.DataFrame:

        """
        Fetch flight data from the Airdata API based on the provided query parameters.

        Parameters:
            since (str or None): 
                Filter flights that started after this date/time (ISO 8601 format). 
                Example: '2025-01-01T00:00:00'.
            until (str or None): 
                Filter flights that started before this date/time (ISO 8601 format).
                Example: '2025-03-31T23:59:59'.
            detail_level (bool): 
                If True, returns comprehensive flight details. If False, returns basic information.
                Maps to 'detail_level=comprehensive' or 'basic' in API request.
            limit (int or None): 
                Maximum number of results to return. Default is None (no limit specified).
            created_after (str or None): 
                Filter flights created after the given date/time (ISO 8601 format).
            battery_ids (list or None): 
                List of battery IDs to filter flights by associated battery.
            pilot_ids (list or None): 
                List of pilot IDs to filter flights by pilot.
            location (list or None): 
                Optional geographic coordinates as a two-item list `[latitude, longitude]` 
                to filter flights near that location.

        Returns:
            pd.DataFrame: A DataFrame containing the retrieved flight data. 
                        If the request fails or no data is found, returns an empty DataFrame.

        Raises:
            ValueError: 
                If `location` is not a list of exactly two numeric values (latitude and longitude).
        """

        # Validate location format: must be None or a list with exactly 2 numeric items
        if location is not None:
            if not isinstance(location, list) or len(location) != 2 or not all(isinstance(x, (int, float)) for x in location):
                raise ValueError("Location must be a list of exactly two numbers: [latitude, longitude]")

        since = format_iso_time(since).replace("T", "+") if since else None
        until = format_iso_time(until).replace("T", "+") if until else None
        created_after = format_iso_time(created_after).replace("T", "+") if created_after else None
        detail_level_str = "comprehensive"

        params = {
            "start": since,
            "end": until,
            "detail_level": detail_level_str,
            "created_after": created_after,
            "battery_ids": ",".join(battery_ids) if battery_ids else None,
            "pilot_ids": ",".join(pilot_ids) if pilot_ids else None,
            "latitude": location[0] if location else None,
            "longitude": location[1] if location else None,
            "limit": limit
        }

        params = {k: v for k, v in params.items() if v is not None}

        url = "/flights?" + "&".join([f"{k}={v}" for k, v in params.items()]) # Construct URL with query string
        
        # Make sure user is authenticated
        if not self.authenticated:
            print("Cannot fetch flights: Not authenticated.")
            return None
                
        try:
            conn = http.client.HTTPSConnection(self.base_url)
            conn.request("GET", url, headers=self.auth_header)
            res = conn.getresponse()

            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                if "data" in data: # to-do : automatically identify the column to normalize
                    normalized_data = list(tqdm(data["data"], desc="Downloading"))
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


def df_to_gdf(
    df: pd.DataFrame,
    lon_col: str = 'longitude',
    lat_col: str = 'latitude',
    ) -> gpd.GeoDataFrame:
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
            crs=4326
        )
    except Exception as e:
        raise ValueError(f"Failed to create GeoDataFrame: {e}")

    return gdf


def fetch_data(
    df: pd.DataFrame,
    filter_ids: list | None = None,
    log_errors: bool = True,
    ) -> pd.DataFrame:
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
    required_cols = {'id', 'csvLink'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Input DataFrame must contain columns: {required_cols}")

    if filter_ids is not None:
        df = df[df['id'].isin(filter_ids)]

    all_combined_rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
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

    df = pd.concat(all_combined_rows, ignore_index=True)

    columns_to_drop = [
        "displayLink", "csvLink", "kmlLink", "gpxLink", "originalLink", "participants.object",
        "flightApp.name", "flightApp.version", "batteryPercent.takeOff", "batteryPercent.landing",
        "satellites", "gpslevel", "voltage(v)", "xSpeed(mph)", "ySpeed(mph)", "zSpeed(mph)",
        "compass_heading(degrees)", "pitch(degrees)", "roll(degrees)", "isPhoto", "isVideo",
        "rc_elevator", "rc_aileron", "rc_throttle", "rc_rudder", "rc_elevator(percent)",
        "rc_aileron(percent)", "rc_throttle(percent)", "rc_rudder(percent)",
        "gimbal_heading(degrees)", "gimbal_pitch(degrees)", "gimbal_roll(degrees)",
        "battery_percent", "voltageCell1", "voltageCell2", "voltageCell3",
        "voltageCell4", "voltageCell5", "voltageCell6", "current(A)",
        "pitch(degrees)", "roll(degrees)", "batteries.object", "object"
    ]

    df = df.drop(columns=columns_to_drop, errors='ignore')
    cols = ["participants.data", "batteries.data"]

    dfs_to_join = []

    for col in cols:
        try:
            expanded = pd.json_normalize(df[col].explode(ignore_index=True))
            expanded.columns = [f"{col}.{subcol}" for subcol in expanded.columns]
            dfs_to_join.append(expanded)
        except Exception as e:
            if log_errors:
                print(f"Error expanding column '{col}': {e}")

    if dfs_to_join:
        expanded_df = pd.concat(dfs_to_join, axis=1)

    df = df.join(expanded_df).drop(columns=cols)
    return df_to_gdf(df)


def points_to_segment(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
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
    for flight_id in tqdm(gdf['id'].unique(), desc="Creating segments"):
        flight_data = gdf[gdf['id'] == flight_id].sort_values(by='time(millisecond)')
        assert flight_data['time(millisecond)'].is_monotonic_increasing, f"time(millisecond) is not ascending for id: {flight_id}"

        flight_data = flight_data.reset_index(drop=True)
        for i in range(len(flight_data) - 1):
            pt1 = flight_data.loc[i, 'geometry']
            pt2 = flight_data.loc[i + 1, 'geometry']
            segment = LineString([pt1, pt2])
            # compute distance and time taken 
            # distance_comp = 

            other_cols_data = flight_data.loc[i].drop(['geometry', 'time(millisecond)'])
            seg_dict = {
                'id': flight_id,
                't1': flight_data.loc[i, 'time(millisecond)'],
                't2': flight_data.loc[i + 1, 'time(millisecond)'],
                'geometry': segment
            }
            seg_dict.update(other_cols_data.to_dict())
            segments.append(seg_dict)

    if not segments:
      return gpd.GeoDataFrame(columns=['id', 't1', 't2', 'geometry'])
    
    return gpd.GeoDataFrame(segments, geometry='geometry')


def points_to_line(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Converts a GeoDataFrame with point geometries into a GeoDataFrame with
    LineString geometries for each unique 'id', ordered by 'time(millisecond)'.

    Args:
        gdf: The input GeoDataFrame with 'id', 'time(millisecond)', and 'geometry'
            (Point) columns.

    Returns:
        A new GeoDataFrame where each row represents a unique 'id' and its
        corresponding LineString geometry.
    """

    gdf = gdf[gdf['geometry'] != Point(0, 0)]
    grouped = []
    for flight_id in tqdm(gdf['id'].unique(), desc="Processing flights"):
        flight_data = gdf[gdf['id'] == flight_id].sort_values(by='time(millisecond)')
        assert flight_data['time(millisecond)'].is_monotonic_increasing, f"time(millisecond) is not ascending for id: {flight_id}"
        grouped.append(flight_data)

    gdf_sorted = pd.concat(grouped)
    line_geometries = (
        gdf_sorted.groupby('id')['geometry']
        .apply(lambda x: LineString(x.tolist()) if len(x) > 1 else None)
    )
    line_gdf = gpd.GeoDataFrame(line_geometries, geometry='geometry')
    other_cols = [col for col in gdf.columns if col not in ['geometry', 'time(millisecond)']]
    metadata = gdf[other_cols].drop_duplicates(subset=['id']).set_index('id')

    line_gdf = line_gdf.merge(metadata, left_index=True, right_index=True).reset_index()
    return append_cols(line_gdf, cols='geometry')






  



