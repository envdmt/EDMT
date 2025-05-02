import os
import uuid
import pandas as pd
import pickle
import numpy as np
import geopandas as gpd
# from osgeo import ogr
import requests
from shapely import make_valid

from edmt.contrib import clean_vars


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


"""
A unit of time is any particular time interval, used as a standard way of measuring or
expressing duration.  The base unit of time in the International System of Units (SI),
and by extension most of the Western world, is the second, defined as about 9 billion
oscillations of the caesium atom.

"""

time_chart: dict[str, float] = {
    "seconds": 1.0,
    "minutes": 60.0,  # 1 minute = 60 sec
    "hours": 3600.0,  # 1 hour = 60 minutes = 3600 seconds
    "days": 86400.0,  # 1 day = 24 hours = 1440 min = 86400 sec
    "weeks": 604800.0,  # 1 week=7d=168hr=10080min = 604800 sec
    "months": 2629800.0,  # Approximate value for a month in seconds
    "years": 31557600.0,  # Approximate value for a year in seconds
}

time_chart_inverse: dict[str, float] = {
    key: 1 / value for key, value in time_chart.items()
}


def convert_time(time_value: float, unit_from: str, unit_to: str) -> float:
    """
    Convert time from one unit to another using the time_chart above.

    >>> convert_time(3600, "seconds", "hours")
    1.0
    >>> convert_time(3500, "Seconds", "Hours")
    0.972
    >>> convert_time(1, "DaYs", "hours")
    24.0
    >>> convert_time(120, "minutes", "SeCoNdS")
    7200.0
    >>> convert_time(2, "WEEKS", "days")
    14.0
    >>> convert_time(0.5, "hours", "MINUTES")
    30.0
    >>> convert_time(-3600, "seconds", "hours")
    Traceback (most recent call last):
        ...
    ValueError: 'time_value' must be a non-negative number.
    >>> convert_time("Hello", "hours", "minutes")
    Traceback (most recent call last):
        ...
    ValueError: 'time_value' must be a non-negative number.
    >>> convert_time([0, 1, 2], "weeks", "days")
    Traceback (most recent call last):
        ...
    ValueError: 'time_value' must be a non-negative number.
    >>> convert_time(1, "cool", "century")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Invalid unit cool is not in seconds, minutes, hours, days, weeks, ...
    >>> convert_time(1, "seconds", "hot")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    ValueError: Invalid unit hot is not in seconds, minutes, hours, days, weeks, ...
    """
    if not isinstance(time_value, (int, float)) or time_value < 0:
        msg = "'time_value' must be a non-negative number."
        raise ValueError(msg)

    unit_from = unit_from.lower()
    unit_to = unit_to.lower()
    if unit_from not in time_chart or unit_to not in time_chart:
        invalid_unit = unit_from if unit_from not in time_chart else unit_to
        msg = f"Invalid unit {invalid_unit} is not in {', '.join(time_chart)}."
        raise ValueError(msg)

    return round(
        time_value * time_chart[unit_from] * time_chart_inverse[unit_to],
        3,
    )


if __name__ == "__main__":
    import doctest

    doctest.testmod()
    print(f"{convert_time(3600,'seconds', 'hours') = :,}")
    print(f"{convert_time(360, 'days', 'months') = :,}")
    print(f"{convert_time(360, 'months', 'years') = :,}")
    print(f"{convert_time(1, 'years', 'seconds') = :,}")




"""
Conversion of length units.
Available Units:
Metre, Kilometre, Megametre, Gigametre,
Terametre, Petametre, Exametre, Zettametre, Yottametre

USAGE :
-> Import this file into their respective project.
-> Use the function length_conversion() for conversion of length units.
-> Parameters :
    -> value : The number of from units you want to convert
    -> from_type : From which type you want to convert
    -> to_type : To which type you want to convert
"""

UNIT_SYMBOL = {
    "meter": "m",
    "kilometer": "km",
    "megametre": "Mm",
    "gigametre": "Gm",
    "terametre": "Tm",
    "petametre": "Pm",
    "exametre": "Em",
    "zettametre": "Zm",
    "yottametre": "Ym",
}
# Exponent of the factor(meter)
METRIC_CONVERSION = {
    "m": 0,
    "km": 3,
    "Mm": 6,
    "Gm": 9,
    "Tm": 12,
    "Pm": 15,
    "Em": 18,
    "Zm": 21,
    "Ym": 24,
}


def length_conversion(value: float, from_type: str, to_type: str) -> float:
    """
    Conversion between astronomical length units.

    >>> length_conversion(1, "meter", "kilometer")
    0.001
    >>> length_conversion(1, "meter", "megametre")
    1e-06
    >>> length_conversion(1, "gigametre", "meter")
    1000000000
    >>> length_conversion(1, "gigametre", "terametre")
    0.001
    >>> length_conversion(1, "petametre", "terametre")
    1000
    >>> length_conversion(1, "petametre", "exametre")
    0.001
    >>> length_conversion(1, "terametre", "zettametre")
    1e-09
    >>> length_conversion(1, "yottametre", "zettametre")
    1000
    >>> length_conversion(4, "wrongUnit", "inch")
    Traceback (most recent call last):
      ...
    ValueError: Invalid 'from_type' value: 'wrongUnit'.
    Conversion abbreviations are: m, km, Mm, Gm, Tm, Pm, Em, Zm, Ym
    """

    from_sanitized = from_type.lower().strip("s")
    to_sanitized = to_type.lower().strip("s")

    from_sanitized = UNIT_SYMBOL.get(from_sanitized, from_sanitized)
    to_sanitized = UNIT_SYMBOL.get(to_sanitized, to_sanitized)

    if from_sanitized not in METRIC_CONVERSION:
        msg = (
            f"Invalid 'from_type' value: {from_type!r}.\n"
            f"Conversion abbreviations are: {', '.join(METRIC_CONVERSION)}"
        )
        raise ValueError(msg)
    if to_sanitized not in METRIC_CONVERSION:
        msg = (
            f"Invalid 'to_type' value: {to_type!r}.\n"
            f"Conversion abbreviations are: {', '.join(METRIC_CONVERSION)}"
        )
        raise ValueError(msg)
    from_exponent = METRIC_CONVERSION[from_sanitized]
    to_exponent = METRIC_CONVERSION[to_sanitized]
    exponent = 1

    if from_exponent > to_exponent:
        exponent = from_exponent - to_exponent
    else:
        exponent = -(to_exponent - from_exponent)

    return value * pow(10, exponent)


if __name__ == "__main__":
    from doctest import testmod

    testmod()



"""
Convert speed units
"""

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


def convert_speed(speed: float, unit_from: str, unit_to: str) -> float:
    """
    Convert speed from one unit to another using the speed_chart above.

    "km/h": 1.0,
    "m/s": 3.6,
    "mph": 1.609344,
    "knot": 1.852,

    >>> convert_speed(100, "km/h", "m/s")
    27.778
    >>> convert_speed(100, "km/h", "mph")
    62.137
    >>> convert_speed(100, "km/h", "knot")
    53.996
    >>> convert_speed(100, "m/s", "km/h")
    360.0
    >>> convert_speed(100, "m/s", "mph")
    223.694
    >>> convert_speed(100, "m/s", "knot")
    194.384
    >>> convert_speed(100, "mph", "km/h")
    160.934
    >>> convert_speed(100, "mph", "m/s")
    44.704
    >>> convert_speed(100, "mph", "knot")
    86.898
    >>> convert_speed(100, "knot", "km/h")
    185.2
    >>> convert_speed(100, "knot", "m/s")
    51.444
    >>> convert_speed(100, "knot", "mph")
    115.078
    """
    if unit_to not in speed_chart or unit_from not in speed_chart_inverse:
        msg = (
            f"Incorrect 'from_type' or 'to_type' value: {unit_from!r}, {unit_to!r}\n"
            f"Valid values are: {', '.join(speed_chart_inverse)}"
        )
        raise ValueError(msg)
    return round(speed * speed_chart[unit_from] * speed_chart_inverse[unit_to], 3)


if __name__ == "__main__":
    import doctest

    doctest.testmod()



# def read_file_from_url(url_path: str, local_file: str = "downloaded_file"):
#     """
#     Reads a file from a given URL, downloads it locally, and loads it as a GeoDataFrame.

#     Parameters:
#     ----------
#     url_path : str
#         The URL of the file to download.
#     local_file : str, optional
#         The name of the local file to save the downloaded content (default: "downloaded_file").

#     Returns:
#     -------
#     gpd.GeoDataFrame
#         A GeoDataFrame loaded from the downloaded file.

#     Raises:
#     ------
#     ValueError:
#         If `url_path` is None or empty.
#     requests.exceptions.RequestException:
#         If there is an issue during the HTTP request.
#     OSError:
#         If there is an issue writing the local file.
#     """
#     if not url_path:
#         raise ValueError("The 'url_path' parameter cannot be None or empty.")
    
#     try:
#         # Download the file from the given URL
#         with requests.get(url_path, stream=True) as response:
#             response.raise_for_status()
#             with open(local_file, "wb") as file:
#                 for chunk in response.iter_content(chunk_size=8192):
#                     file.write(chunk)
        
#         # Load the file into a GeoDataFrame
#         gdf = gpd.read_file(local_file, engine="pyogrio")
#         return gdf
    
#     except requests.exceptions.RequestException as e:
#         raise requests.exceptions.RequestException(f"Error fetching file from URL: {e}")
    
#     except OSError as e:
#         raise OSError(f"Error saving or accessing the local file: {e}")
    
#     finally:
#         # Optional: Clean up the local file after reading if needed
#         if os.path.exists(local_file):
#             os.remove(local_file)