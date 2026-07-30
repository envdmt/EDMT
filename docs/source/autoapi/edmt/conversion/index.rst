edmt.conversion
===============

.. py:module:: edmt.conversion


Submodules
----------

.. toctree::
   :maxdepth: 1

   /autoapi/edmt/conversion/conversion/index




Package Contents
----------------

.. py:function:: sdf_to_gdf(sdf, crs=None)

   Converts a spatial DataFrame to a GeoDataFrame with optional CRS assignment.

   :param sdf: Input spatial DataFrame containing geometry column.
   :type sdf: pd.DataFrame
   :param crs: Coordinate Reference System. Defaults to EPSG:4326.
   :type crs: str or int, optional

   :returns: A cleaned GeoDataFrame with valid geometries.
   :rtype: gpd.GeoDataFrame

   :raises ValueError: If input is not a DataFrame or is empty.


.. py:function:: generate_uuid(df: pandas.DataFrame, *, force: bool = False, index: bool = False, uuid_col: str = 'uuid', detect_uuid_cols: bool = True, detect_contains: tuple[str, Ellipsis] = ('uuid', )) -> pandas.DataFrame

   Ensure a pandas DataFrame contains a column of valid UUIDs, creating or repairing as needed.

   This function adds a new UUID column or validates/repairs an existing one. It can optionally
   detect existing UUID-like columns to avoid duplication and control column placement.

   :param df: Input DataFrame to process.
   :type df: pd.DataFrame
   :param force: If True, always generate new UUIDs—even if a valid UUID column already exists
                 (default: False).
   :type force: bool, optional
   :param index: If True, place the UUID column at the beginning of the DataFrame; otherwise,
                 place it at the end (default: False).
   :type index: bool, optional
   :param uuid_col: Name of the target UUID column (default: "uuid").
   :type uuid_col: str, optional
   :param detect_uuid_cols: If True and `force=False`, scan for existing columns that appear to contain UUIDs
                            (based on name and content) to avoid redundant generation (default: True).
   :type detect_uuid_cols: bool, optional
   :param detect_contains: Substrings used to identify potential UUID columns by name when `detect_uuid_cols=True`
                           (default: ("uuid",)).
   :type detect_contains: tuple of str, optional

   :returns: A copy of the input DataFrame with a valid UUID column named `uuid_col`.
   :rtype: pd.DataFrame

   :raises ValueError: If input is not a DataFrame or if the DataFrame is empty.

   .. rubric:: Notes

   - A value is considered a valid UUID if it is a string matching the standard UUID format
     (e.g., "f47ac10b-58cc-4372-a567-0e02b2c3d479").
   - When `force=False` and a UUID-like column is detected (by name and content), the function
     reuses it but repairs any invalid entries by replacing them with new UUIDs.
   - The output DataFrame is always a copy; the original is not modified.
   - Column ordering is explicitly controlled: UUID column is moved to front if `index=True`,
     otherwise to the back.

   .. rubric:: Examples

   >>> df = pd.DataFrame({"name": ["Alice", "Bob"]})
   >>> df_with_uuid = generate_uuid(df)
   >>> "uuid" in df_with_uuid.columns
   True

   >>> df_existing = pd.DataFrame({"uuid": ["invalid", "7af3ea7c-5a14-48c2-a3c2-b014488c0216"], "val": [1, 2]})
   >>> fixed = generate_uuid(df_existing)
   # First entry replaced with valid UUID; second preserved


.. py:function:: generate_cmap(data: ArrayLike, num_divisions: int, cmap: str = 'viridis') -> Tuple[List[str], List[str]]

   Generate range labels and corresponding hex colors from a colormap.

   :param data: Numeric data used to determine the value range.
   :type data: array-like
   :param num_divisions: Number of intervals to divide the data range into.
   :type num_divisions: int
   :param cmap: Name of the matplotlib colormap.
   :type cmap: str, default="viridis"

   :returns:

             labels :
                 Range labels formatted as "min - max".
             colors :
                 Hexadecimal color codes corresponding to each range.
   :rtype: tuple[list[str], list[str]]

   :raises ValueError: If num_divisions is less than 1 or data is empty.


.. py:function:: get_utm_epsg(longitude=None)

   Generates UTM EPSG code based on longitude.

   :param longitude: Longitude value to determine UTM zone.
   :type longitude: float

   :returns: EPSG code as a string.
   :rtype: str

   :raises KeyError: If longitude is not provided.


.. py:function:: convert_time(value: float, unit_from: str, unit_to: str) -> float

   Converts a given time value between different units.

   :param time_value: The numerical value of the time.
   :type time_value: float
   :param unit_from: The original unit of time.
   :type unit_from: str
   :param unit_to: The target unit to convert to.
   :type unit_to: str

   :returns: The converted time value rounded to 3 decimal places.
   :rtype: float

   :raises ValueError: If units are unsupported or value is invalid.


.. py:function:: convert_speed(speed: float, unit_from: str, unit_to: str) -> float

   Converts speed between different units.

   :param speed: Input speed value.
   :type speed: float
   :param unit_from: Original unit.
   :type unit_from: str
   :param unit_to: Target unit.
   :type unit_to: str

   :returns: Converted speed value.
   :rtype: float

   :raises ValueError: If unit is unsupported.


.. py:function:: convert_distance(value: float, unit_from: str, unit_to: str) -> float

   Converts distance values between metric and imperial units.

   :param value: Input distance value.
   :type value: float
   :param from_type: Original unit.
   :type from_type: str
   :param to_type: Target unit.
   :type to_type: str

   :returns: Converted distance value.
   :rtype: float

   :raises ValueError: If unit is unsupported.


.. py:function:: convert_temperature(value: float, unit_from: str, unit_to: str) -> float

   Converts temperature between different scales.

   :param value: Input temperature value.
   :type value: float
   :param unit_from: Original unit. Supported: C, F, K (also °C, °F, °K).
   :type unit_from: str
   :param unit_to: Target unit. Supported: C, F, K (also °C, °F, °K).
   :type unit_to: str

   :returns: Converted temperature value (rounded to 3 decimals).
   :rtype: float

   :raises ValueError: If unit is unsupported or Kelvin is invalid (< 0).


.. py:function:: format_temperature(value: float, unit: str, symbol: bool = True) -> str

   Formats a temperature value with unit, e.g. '23.5 °C' or '296.6 K'.

   :param value: Temperature value.
   :type value: float
   :param unit: Unit to display (C, F, K).
   :type unit: str
   :param symbol: If True, uses °C/°F, and K without degree symbol.
   :type symbol: bool

   :returns: Formatted temperature string.
   :rtype: str


