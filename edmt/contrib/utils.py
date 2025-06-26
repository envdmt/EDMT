from dateutil import parser
import geopandas as gpd
import pandas as pd

def clean_vars(addl_kwargs={}, **kwargs):
    for k in addl_kwargs.keys():
        print(f"Warning: {k} is a non-standard parameter. Results may be unexpected.")
        clea_ = {k: v for k, v in {**addl_kwargs, **kwargs}.items() if v is not None}
        return clea_


def normalize_column(df, col):
    # print(col)
    for k, v in pd.json_normalize(df.pop(col), sep="__").add_prefix(f"{col}__").items():
        df[k] = v.values


def dataframe_to_dict(events):
    if isinstance(events, gpd.GeoDataFrame):
        events["location"] = pd.DataFrame({"longitude": events.geometry.x, "latitude": events.geometry.y}).to_dict(
            "records"
        )
        del events["geometry"]

    if isinstance(events, pd.DataFrame):
        events = events.to_dict("records")
    return events


def clean_time_cols(df,columns = []):
    if columns:
        time_cols = [columns]
        for col in time_cols:
            if col in df.columns and not pd.api.types.is_datetime64_ns_dtype(df[col]):
                # convert x is not None to pd.isna(x) is False
                df[col] = df[col].apply(lambda x: pd.to_datetime(parser.parse(x), utc=True) if not pd.isna(x) else None)
        return df
    else:
        print("Select a column with Time format")


def format_iso_time(date_string: str) -> str:
    try:
        return pd.to_datetime(date_string).isoformat()
    except ValueError:
        raise ValueError(f"Failed to parse timestamp'{date_string}'")
    

def df_to_gdf(
    df: pd.DataFrame,
    lon_col: str = 'longitude',
    lat_col: str = 'latitude',
    crs: int = 4326
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

    Example:
        >>> data = pd.DataFrame({
        ...     'latitude': [37.7749, 40.7128],
        ...     'longitude': [-122.4194, -74.0060],
        ...     'name': ['San Francisco', 'New York']
        ... })
        >>> gdf = pd_to_gdf(data)
        >>> print(gdf.head())
                             name                   geometry
        0         San Francisco  POINT (-122.41940 37.77490)
        1              New York   POINT (-74.00600 40.71280)
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