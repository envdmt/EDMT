import uuid
import pandas as pd
import geopandas as gpd
from shapely import make_valid
from edmt.contrib.utils import (
    clean_vars
)

"""
A unit of time is any particular time interval, used as a standard way of measuring or
expressing duration.  The base unit of time in the International System of Units (SI),
and by extension most of the Western world, is the second, defined as about 9 billion
oscillations of the caesium atom.

"""

time_chart: dict[str, float] = {
    "microseconds": 0.000001,   # 1 μs = 1e-6 seconds
    "microsecond": 0.000001,
    "µs": 0.000001,
    "milliseconds": 0.001,      # 1 ms = 1e-3 seconds
    "millisecond": 0.001,
    "ms": 0.001,
    "seconds": 1.0,              # Base unit
    "second": 1.0,
    "s": 1.0,
    "minutes": 60.0,             # 1 min = 60 sec
    "minute": 60.0,
    "min": 60.0,
    "m": 60.0,
    "hours": 3600.0,             # 1 hr = 60 min = 3600 sec
    "hour": 3600.0,
    "hr": 3600.0,
    "h": 3600.0,
    "days": 86400.0,             # 1 day = 24 hr = 86400 sec
    "day": 86400.0,
    "d": 86400.0,
    "weeks": 604800.0,           # 1 week = 7 days = 604800 sec
    "week": 604800.0,
    "wk": 604800.0,
    "w": 604800.0,
    "months": 2629800.0,         # Approx. 30.44 days = 1/12 year
    "month": 2629800.0,
    "years": 31557600.0,         # Julian year = 365.25 days
    "year": 31557600.0,
    "yr": 31557600.0,
    "y": 31557600.0,
}

time_chart_inverse: dict[str, float] = {
    key: 1.0 / value for key, value in time_chart.items()
}

speed_chart: dict[str, float] = {
    "km/h": 1.0,
    "m/s": 3.6,
    "mph": 1.609344,
    "knot": 1.852,
}

speed_chart_inverse: dict[str, float] = {
    "km/h": 1.0,
    "m/s": 0.277777778,
    "mph": 0.621371192,
    "knot": 0.539956803,
}

UNIT_SYMBOL = {
    "meter": "m", "meters": "m",
    "kilometer": "km", "kilometers": "km",
    "centimeter": "cm", "centimeters": "cm",
    "millimeter": "mm", "millimeters": "mm",
    "mile": "mi", "miles": "mi",
    "yard": "yd", "yards": "yd",
    "foot": "ft", "feet": "ft",
    "inch": "in", "inches": "in",
}

METRIC_CONVERSION = {
    "mm": -3,
    "cm": -2,
    "dm": -1,
    "m": 0,
    "dam": 1,
    "hm": 2,
    "km": 3,
}

distance_chart = {
    "mm": 0.001,
    "cm": 0.01,
    "dm": 0.1,
    "m": 1.0,
    "dam": 10.0,
    "hm": 100.0,
    "km": 1000.0,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
    "mi": 1609.344,
}

def sdf_to_gdf(sdf, crs=None):
    """
    Converts a spatial dataframe (sdf) to a geodataframe (gdf) with a user-defined CRS.

    Parameters:
    - sdf: Spatial DataFrame to convert.
    - crs: Coordinate Reference System (default is EPSG:4326).

    Steps:
    1. Creates a copy of the input spatial dataframe to avoid modifying the original.
    2. Filters out rows where the 'SHAPE' column is NaN (invalid geometries).
    3. Converts the filtered dataframe to a GeoDataFrame using the 'SHAPE' column for geometry and sets the CRS.
    4. Applies the `make_valid` function to the geometry column to correct any invalid geometries.
    5. Drops the columns 'Shape__Area', 'Shape__Length', and 'SHAPE', if they exist, to clean up the GeoDataFrame.
    6. Returns the resulting GeoDataFrame.
    """
    # Validate input DataFrame
    if not isinstance(sdf, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if sdf.empty:
        raise ValueError("DataFrame is empty. Cannot generate UUIDs for an empty DataFrame.")

    # clean vars
    params = clean_vars(
        shape = "SHAPE",
        geometry = "geometry",
        columns = ["Shape__Area", "Shape__Length", "SHAPE"],
        crs=crs
    )
    assert params.get("geometry") is None
    print("Geometry column is present and valid")

    tmp = sdf.copy()
    tmp = tmp[~tmp[params.get("shape")].isna()]

    if crs:
        crs=params.get("crs")
    else:
        crs=4326

    gdf = gpd.GeoDataFrame(
        tmp, 
        geometry=tmp[params.get("shape")], 
        crs=crs
        )
    gdf['geometry'] = gdf[params.get("geometry")].apply(lambda x: make_valid(x)) # Validate geometries
    gdf.drop(columns=params.get("columns"), errors='ignore', inplace=True)
    print("COnverted Spatial DataFrame to GeoDataFrame")
    return gdf

def generate_uuid(df, index=False):
    """
    Adds a unique 'uuid' column with UUIDs to the DataFrame if no existing UUID-like column is found.
    Does not generate new UUIDs if UUIDs are already assigned in a 'uuid' column.

    Args:
        df (pd.DataFrame): The DataFrame to which UUIDs will be added.
        index (bool): If True, sets 'uuid' as the index. Otherwise, 'uuid' remains a column.

    Returns:
        pd.DataFrame: DataFrame with a 'uuid' column added if no UUID-like column exists.
    Raises:
        ValueError: If 'df' is not a DataFrame or if it's empty.
    """

    # Validate input DataFrame
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("DataFrame is empty. Cannot generate UUIDs for an empty DataFrame.")

    # Define UUID pattern
    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'

    # Check for existing UUID-like columns
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) and df[col].str.match(uuid_pattern).all():
            print(f"Column '{col}' contains UUID-like values.")
            if index:
                return df.set_index(col).reset_index()
            else:
                return df  #

    print("No UUID-like column found. Generating 'uuid' column in the DataFrame.")

    if 'uuid' not in df.columns:
        df['uuid'] = [str(uuid.uuid4()).lower() for _ in range(len(df))]
    else:
        df['uuid'] = df['uuid'].apply(lambda x: x if pd.notnull(x) else str(uuid.uuid4()).lower())

    if index:
        df = df.set_index('uuid').reset_index()

    return df
       
def get_utm_epsg(longitude=None):
    if longitude is None:
       print("KeyError : Select column with longitude values")
    else:
        zone_number = int((longitude + 180) / 6) + 1
        hemisphere = '6' if longitude >= 0 else '7'  # 6 for Northern, 7 for Southern Hemisphere
        return f"32{hemisphere}{zone_number:02d}"
    
def to_gdf(df):
    longitude, latitude = (0, 1) if isinstance(df["location"].iat[0], list) else ("longitude", "latitude")
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["location"].str[longitude], df["location"].str[latitude]),
        crs=4326,
    )

def convert_time(time_value: float, unit_from: str, unit_to: str) -> float:
    """
    Converts a given time value between different units.

    Args:
        time_value (float): The numerical value of the time.
        unit_from (str): The original unit of time.
        unit_to (str): The target unit to convert to.

    Returns:
        float: The converted time value.

    Raises:
        ValueError: If the provided units are not supported or value is invalid.
    """
    if not isinstance(time_value, (int, float)) or time_value < 0:
        raise ValueError("'time_value' must be a non-negative number.")

    # Normalize input unit names
    unit_from = unit_from.lower().strip()
    unit_to = unit_to.lower().strip()

    unit_from = {
        "us": "microseconds",
        "μs": "microseconds",
        "microsec": "microseconds",
        "usec": "microseconds"
    }.get(unit_from, unit_from)

    unit_to = {
        "us": "microseconds",
        "μs": "microseconds",
        "microsec": "microseconds",
        "usec": "microseconds"
    }.get(unit_to, unit_to)

    if unit_from not in time_chart:
        raise ValueError(f"Invalid 'unit_from': {unit_from}. Supported units: {', '.join(time_chart.keys())}")
    if unit_to not in time_chart:
        raise ValueError(f"Invalid 'unit_to': {unit_to}. Supported units: {', '.join(time_chart.keys())}")

    # Convert to seconds first, then to target unit
    seconds = time_value * time_chart[unit_from]
    converted = seconds / time_chart[unit_to]

    return round(converted, 3)

def convert_speed(speed: float, unit_from: str, unit_to: str) -> float:
    if unit_to not in speed_chart or unit_from not in speed_chart_inverse:
        msg = (
            f"Incorrect 'from_type' or 'to_type' value: {unit_from!r}, {unit_to!r}\n"
            f"Valid values are: {', '.join(speed_chart_inverse)}"
        )
        raise ValueError(msg)
    return round(speed * speed_chart[unit_from] * speed_chart_inverse[unit_to], 3)

def convert_distance(value: float, from_type: str, to_type: str) -> float:
    """
    Converts distance values between different units including metric and imperial.

    Supports:
        Metric: mm, cm, dm, m, dam, hm, km
        Imperial: in, ft, yd, mi

    Handles plural forms, full names, and inconsistent casing.
    """

    from_sanitized = from_type.lower().strip("s")
    to_sanitized = to_type.lower().strip("s")

    from_sanitized = UNIT_SYMBOL.get(from_sanitized, from_sanitized)
    to_sanitized = UNIT_SYMBOL.get(to_sanitized, to_sanitized)

    valid_units = set(distance_chart.keys())
    if from_sanitized not in valid_units:
        raise ValueError(f"Invalid 'from_type': {from_type!r}. Valid units: {', '.join(valid_units)}")
    if to_sanitized not in valid_units:
        raise ValueError(f"Invalid 'to_type': {to_type!r}. Valid units: {', '.join(valid_units)}")

    if from_sanitized in METRIC_CONVERSION and to_sanitized in METRIC_CONVERSION:
        from_exp = METRIC_CONVERSION[from_sanitized]
        to_exp = METRIC_CONVERSION[to_sanitized]
        exponent_diff = from_exp - to_exp
        return round(value * pow(10, exponent_diff), 3)

    value_in_meters = value * distance_chart[from_sanitized]
    converted = value_in_meters / distance_chart[to_sanitized]

    return round(converted, 3)
