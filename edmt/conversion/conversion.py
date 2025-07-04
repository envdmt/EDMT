"""
EDMT Utilities Module

This module contains utility functions for:
- Time, speed, and distance unit conversion
- Spatial DataFrame to GeoDataFrame conversion
- UUID generation
"""

import uuid
import pandas as pd
import geopandas as gpd
from shapely import make_valid
from edmt.contrib.utils import clean_vars


"""
Time Unit Conversion Chart

A dictionary mapping time units to their equivalent in seconds.
Used for converting between different time units like hours to milliseconds.
"""
time_chart: dict[str, float] = {
    "microseconds": 0.000001,
    "microsecond": 0.000001,
    "µs": 0.000001,
    "milliseconds": 0.001,
    "millisecond": 0.001,
    "ms": 0.001,
    "seconds": 1.0,
    "second": 1.0,
    "s": 1.0,
    "minutes": 60.0,
    "minute": 60.0,
    "min": 60.0,
    "m": 60.0,
    "hours": 3600.0,
    "hour": 3600.0,
    "hr": 3600.0,
    "h": 3600.0,
    "days": 86400.0,
    "day": 86400.0,
    "d": 86400.0,
    "weeks": 604800.0,
    "week": 604800.0,
    "wk": 604800.0,
    "w": 604800.0,
    "months": 2629800.0,
    "month": 2629800.0,
    "years": 31557600.0,
    "year": 31557600.0,
    "yr": 31557600.0,
    "y": 31557600.0,
}

# Inverse of time_chart for reverse lookup
time_chart_inverse: dict[str, float] = {
    key: 1.0 / value for key, value in time_chart.items()
}

# Speed unit conversion factors relative to km/h
speed_chart: dict[str, float] = {
    "km/h": 1.0,
    "m/s": 3.6,
    "mph": 1.609344,
    "knot": 1.852,
}

# Inverse speed chart for faster reverse conversions
speed_chart_inverse: dict[str, float] = {
    "km/h": 1.0,
    "m/s": 0.277777778,
    "mph": 0.621371192,
    "knot": 0.539956803,
}

# Mapping full unit names to standard symbols
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

# Metric prefix powers of ten
METRIC_CONVERSION = {
    "mm": -3,
    "cm": -2,
    "dm": -1,
    "m": 0,
    "dam": 1,
    "hm": 2,
    "km": 3,
}

# Distance unit to meter conversion factors
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
    Converts a spatial DataFrame to a GeoDataFrame with optional CRS assignment.

    Args:
        sdf (pd.DataFrame): Input spatial DataFrame containing geometry column.
        crs (str or int, optional): Coordinate Reference System. Defaults to EPSG:4326.

    Returns:
        gpd.GeoDataFrame: A cleaned GeoDataFrame with valid geometries.

    Raises:
        ValueError: If input is not a DataFrame or is empty.

    Example:
        >>> sdf = pd.read_csv("spatial_data.csv")
        >>> gdf = sdf_to_gdf(sdf)
    """
    if not isinstance(sdf, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if sdf.empty:
        raise ValueError("DataFrame is empty.")

    params = clean_vars(
        shape="SHAPE",
        geometry="geometry",
        columns=["Shape__Area", "Shape__Length", "SHAPE"],
        crs=crs
    )

    tmp = sdf.copy()
    tmp = tmp[~tmp[params.get("shape")].isna()]

    gdf = gpd.GeoDataFrame(tmp, geometry=tmp[params.get("shape")], crs=params.get("crs", 4326))
    gdf['geometry'] = gdf.geometry.apply(make_valid)
    gdf.drop(columns=params.get("columns"), errors='ignore', inplace=True)

    return gdf


def generate_uuid(df, index=False):
    """
    Adds a 'uuid' column to the DataFrame if no existing UUID-like column exists.

    Args:
        df (pd.DataFrame): The DataFrame to add UUIDs to.
        index (bool): Whether to set 'uuid' as the DataFrame index.

    Returns:
        pd.DataFrame: DataFrame with UUIDs added if needed.

    Raises:
        ValueError: If input is not a DataFrame or is empty.

    Example:
        >>> df = pd.DataFrame({"name": ["Alice", "Bob"]})
        >>> df = generate_uuid(df)
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("DataFrame is empty.")

    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'

    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) and df[col].str.match(uuid_pattern).all():
            if index:
                return df.set_index(col).reset_index()
            else:
                return df

    if 'uuid' not in df.columns:
        df['uuid'] = [str(uuid.uuid4()).lower() for _ in range(len(df))]
    else:
        df['uuid'] = df['uuid'].apply(lambda x: x if pd.notnull(x) else str(uuid.uuid4()).lower())

    if index:
        df = df.set_index('uuid').reset_index()

    return df


def get_utm_epsg(longitude=None):
    """
    Generates UTM EPSG code based on longitude.

    Args:
        longitude (float): Longitude value to determine UTM zone.

    Returns:
        str: EPSG code as a string.

    Raises:
        KeyError: If longitude is not provided.

    Example:
        >>> epsg = get_utm_epsg(36.82)
    """
    if longitude is None:
        raise KeyError("Select column with longitude values")

    zone_number = int((longitude + 180) / 6) + 1
    hemisphere = '6' if longitude >= 0 else '7'
    return f"32{hemisphere}{zone_number:02d}"


def to_gdf(df):
    """
    Converts a DataFrame with location data into a GeoDataFrame with point geometries.

    Args:
        df (pd.DataFrame): Input DataFrame with location data.

    Returns:
        gpd.GeoDataFrame: GeoDataFrame with point geometries.

    Example:
        >>> df = pd.DataFrame({"location": [[36.82, -1.29], [39.67, -0.09]]})
        >>> gdf = to_gdf(df)
    """
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
        float: The converted time value rounded to 3 decimal places.

    Raises:
        ValueError: If units are unsupported or value is invalid.

    Example:
        >>> convert_time(2, 'hours', 'minutes')
        120.0
    """
    if not isinstance(time_value, (int, float)) or time_value < 0:
        raise ValueError("'time_value' must be a non-negative number.")

    unit_from = unit_from.lower().strip()
    unit_to = unit_to.lower().strip()

    unit_from = {"us": "microseconds", "μs": "microseconds", "microsec": "microseconds", "usec": "microseconds"}.get(unit_from, unit_from)
    unit_to = {"us": "microseconds", "μs": "microseconds", "microsec": "microseconds", "usec": "microseconds"}.get(unit_to, unit_to)

    if unit_from not in time_chart:
        raise ValueError(f"Invalid 'unit_from': {unit_from}. Supported units: {', '.join(time_chart.keys())}")
    if unit_to not in time_chart:
        raise ValueError(f"Invalid 'unit_to': {unit_to}. Supported units: {', '.join(time_chart.keys())}")

    seconds = time_value * time_chart[unit_from]
    converted = seconds / time_chart[unit_to]

    return round(converted, 3)


def convert_speed(speed: float, unit_from: str, unit_to: str) -> float:
    """
    Converts speed between different units.

    Args:
        speed (float): Input speed value.
        unit_from (str): Original unit.
        unit_to (str): Target unit.

    Returns:
        float: Converted speed value.

    Raises:
        ValueError: If unit is unsupported.

    Example:
        >>> convert_speed(60, 'km/h', 'mph')
        37.282
    """
    if unit_to not in speed_chart or unit_from not in speed_chart_inverse:
        msg = (
            f"Incorrect 'from_type' or 'to_type' value: {unit_from!r}, {unit_to!r}\n"
            f"Valid values are: {', '.join(speed_chart_inverse)}"
        )
        raise ValueError(msg)
    return round(speed * speed_chart[unit_from] * speed_chart_inverse[unit_to], 3)


def convert_distance(value: float, from_type: str, to_type: str) -> float:
    """
    Converts distance values between metric and imperial units.

    Args:
        value (float): Input distance value.
        from_type (str): Original unit.
        to_type (str): Target unit.

    Returns:
        float: Converted distance value.

    Raises:
        ValueError: If unit is unsupported.

    Example:
        >>> convert_distance(100, 'm', 'km')
        0.1
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