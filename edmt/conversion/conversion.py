import uuid
import pandas as pd
import geopandas as gpd
from shapely import make_valid
from edmt.contrib.utils import clean_vars

# Time unit conversion factors relative to seconds
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


temp_units: tuple[str, ...] = ("C", "F", "K")

temp_unit_aliases: dict[str, str] = {
    "c": "C",
    "°c": "C",
    "celsius": "C",

    "f": "F",
    "°f": "F",
    "fahrenheit": "F",

    "k": "K",
    "°k": "K",
    "kelvin": "K",
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
    tmp = tmp[~tmp[params["shape"]].isna()]

    gdf = gpd.GeoDataFrame(tmp, geometry=tmp[params["shape"]], crs=params["crs"])
    gdf['geometry'] = gdf.geometry.apply(make_valid)
    gdf.drop(columns=params.get("columns"), errors='ignore', inplace=True)

    return gdf


def _is_valid_uuid(val) -> bool:
    if pd.isna(val):
        return False
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False


def generate_uuid(df: pd.DataFrame, index: bool = False) -> pd.DataFrame:
    """
    Ensures a valid UUID string column named 'uuid' exists in the DataFrame.

    - Creates a 'uuid' column if missing
    - Replaces invalid or missing UUID values
    - Preserves valid UUIDs
    - Optionally sets 'uuid' as index while keeping the column

    Args:
        df (pd.DataFrame): Input DataFrame
        index (bool): Whether to set 'uuid' as the index

    Returns:
        pd.DataFrame

    Raises:
        ValueError: If input is not a DataFrame or is empty
    """
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("DataFrame is empty.")

    df = df.copy()
    if "uuid" not in df.columns:
        df["uuid"] = [str(uuid.uuid4()) for _ in range(len(df))]
    else:
        df["uuid"] = [
            str(val) if _is_valid_uuid(val) else str(uuid.uuid4())
            for val in df["uuid"]
        ]

    df["uuid"] = df["uuid"].astype(str)

    if index:
        df = df.set_index("uuid", drop=False)

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

    """
    if not isinstance(time_value, (int, float)) or time_value < 0:
        raise ValueError("'time_value' must be a non-negative number.")

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


def _norm_temp_unit(unit: str) -> str:
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("Temperature unit must be a non-empty string.")
    u = unit.strip().lower()
    return temp_unit_aliases.get(u, unit.strip().upper())


def _to_celsius(value: float, unit_from: str) -> float:
    u = _norm_temp_unit(unit_from)
    if u == "C":
        return float(value)
    if u == "F":
        return (float(value) - 32.0) * (5.0 / 9.0)
    if u == "K":
        if float(value) < 0.0:
            raise ValueError("Kelvin cannot be below 0.")
        return float(value) - 273.15
    raise ValueError(f"Unsupported temperature unit: {unit_from!r}")


def _from_celsius(c: float, unit_to: str) -> float:
    u = _norm_temp_unit(unit_to)
    if u == "C":
        return float(c)
    if u == "F":
        return float(c) * (9.0 / 5.0) + 32.0
    if u == "K":
        k = float(c) + 273.15
        if k < 0.0:
            raise ValueError("Resulting Kelvin cannot be below 0.")
        return k
    raise ValueError(f"Unsupported temperature unit: {unit_to!r}")


def convert_temperature(value: float, unit_from: str, unit_to: str) -> float:
    """
    Converts temperature between different scales.

    Args:
        value (float): Input temperature value.
        unit_from (str): Original unit. Supported: C, F, K (also °C, °F, °K).
        unit_to (str): Target unit. Supported: C, F, K (also °C, °F, °K).

    Returns:
        float: Converted temperature value (rounded to 3 decimals).

    Raises:
        ValueError: If unit is unsupported or Kelvin is invalid (< 0).

    """
    u_from = _norm_temp_unit(unit_from)
    u_to = _norm_temp_unit(unit_to)

    if u_from not in temp_units or u_to not in temp_units:
        msg = (
            f"Incorrect 'unit_from' or 'unit_to' value: {unit_from!r}, {unit_to!r}\n"
            f"Valid values are: {', '.join(temp_units)}"
        )
        raise ValueError(msg)

    c = _to_celsius(float(value), u_from)
    out = _from_celsius(c, u_to)
    return round(out, 3)


def format_temperature(value: float, unit: str, decimals: int = 1, symbol: bool = True) -> str:
    """
    Formats a temperature value with unit, e.g. '23.5 °C' or '296.6 K'.

    Args:
        value (float): Temperature value.
        unit (str): Unit to display (C, F, K).
        decimals (int): Decimal places.
        symbol (bool): If True, uses °C/°F, and K without degree symbol.

    Returns:
        str: Formatted temperature string.
    """
    u = _norm_temp_unit(unit)
    if u not in temp_units:
        raise ValueError(f"Unsupported temperature unit: {unit!r}. Valid: {', '.join(temp_units)}")

    val_str = f"{float(value):.{int(decimals)}f}"

    if not symbol:
        return f"{val_str} {u}"

    if u in ("C", "F"):
        return f"{val_str} °{u}"
    return f"{val_str} K"
