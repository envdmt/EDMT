edmt.conversion.conversion
==========================

.. py:module:: edmt.conversion.conversion






Module Contents
---------------

.. py:data:: time_chart
   :type:  dict[str, float]

.. py:data:: time_chart_inverse
   :type:  dict[str, float]

.. py:data:: speed_chart
   :type:  dict[str, float]

.. py:data:: speed_chart_inverse
   :type:  dict[str, float]

.. py:data:: UNIT_SYMBOL

.. py:data:: METRIC_CONVERSION

.. py:data:: distance_chart

.. py:data:: temp_units
   :type:  tuple[str, Ellipsis]
   :value: ('C', 'F', 'K')


.. py:data:: temp_unit_aliases
   :type:  dict[str, str]

.. py:function:: sdf_to_gdf(sdf, crs=None)

   Converts a spatial DataFrame to a GeoDataFrame with optional CRS assignment.

   Args:
       sdf (pd.DataFrame): Input spatial DataFrame containing geometry column.
       crs (str or int, optional): Coordinate Reference System. Defaults to EPSG:4326.

   Returns:
       gpd.GeoDataFrame: A cleaned GeoDataFrame with valid geometries.

   Raises:
       ValueError: If input is not a DataFrame or is empty.



.. py:function:: _is_valid_uuid(val) -> bool

.. py:function:: _find_uuid_like_column(df: pandas.DataFrame, contains: tuple[str, Ellipsis] = ('uuid', )) -> Optional[str]

   Return the first column name that looks like it contains a uuid marker.
   E.g. 'uuid', 'UUID', 'user_uuid', 'myUuid', etc.


.. py:function:: generate_uuid(df: pandas.DataFrame, *, force: bool = False, index: bool = False, uuid_col: str = 'uuid', detect_uuid_cols: bool = True, detect_contains: tuple[str, Ellipsis] = ('uuid', )) -> pandas.DataFrame

   Ensure a pandas DataFrame contains a column of valid UUIDs, creating or repairing as needed.

   This function adds a new UUID column or validates/repairs an existing one. It can optionally 
   detect existing UUID-like columns to avoid duplication and control column placement.

   Parameters
   ----------
   df : pd.DataFrame
       Input DataFrame to process.
   force : bool, optional
       If True, always generate new UUIDs—even if a valid UUID column already exists 
       (default: False).
   index : bool, optional
       If True, place the UUID column at the beginning of the DataFrame; otherwise, 
       place it at the end (default: False).
   uuid_col : str, optional
       Name of the target UUID column (default: "uuid").
   detect_uuid_cols : bool, optional
       If True and `force=False`, scan for existing columns that appear to contain UUIDs 
       (based on name and content) to avoid redundant generation (default: True).
   detect_contains : tuple of str, optional
       Substrings used to identify potential UUID columns by name when `detect_uuid_cols=True` 
       (default: ("uuid",)).

   Returns
   -------
   pd.DataFrame
       A copy of the input DataFrame with a valid UUID column named `uuid_col`.

   Raises
   ------
   ValueError
       If input is not a DataFrame or if the DataFrame is empty.

   Notes
   -----
   - A value is considered a valid UUID if it is a string matching the standard UUID format 
     (e.g., "f47ac10b-58cc-4372-a567-0e02b2c3d479").
   - When `force=False` and a UUID-like column is detected (by name and content), the function 
     reuses it but repairs any invalid entries by replacing them with new UUIDs.
   - The output DataFrame is always a copy; the original is not modified.
   - Column ordering is explicitly controlled: UUID column is moved to front if `index=True`, 
     otherwise to the back.

   Examples
   --------
   >>> df = pd.DataFrame({"name": ["Alice", "Bob"]})
   >>> df_with_uuid = generate_uuid(df)
   >>> "uuid" in df_with_uuid.columns
   True

   >>> df_existing = pd.DataFrame({"uuid": ["invalid", "7af3ea7c-5a14-48c2-a3c2-b014488c0216"], "val": [1, 2]})
   >>> fixed = generate_uuid(df_existing)
   # First entry replaced with valid UUID; second preserved


.. py:function:: get_utm_epsg(longitude=None)

   Generates UTM EPSG code based on longitude.

   Args:
       longitude (float): Longitude value to determine UTM zone.

   Returns:
       str: EPSG code as a string.

   Raises:
       KeyError: If longitude is not provided.



.. py:function:: convert_time(value: float, unit_from: str, unit_to: str) -> float

   Converts a given time value between different units.

   Args:
       time_value (float): The numerical value of the time.
       unit_from (str): The original unit of time.
       unit_to (str): The target unit to convert to.

   Returns:
       float: The converted time value rounded to 3 decimal places.

   Raises:
       ValueError: If units are unsupported or value is invalid.



.. py:function:: convert_speed(speed: float, unit_from: str, unit_to: str) -> float

   Converts speed between different units.

   Args:
       speed (float): Input speed value.
       unit_from (str): Original unit.
       unit_to (str): Target unit.

   Returns:
       float: Converted speed value.

   Raises:
       ValueError: If unit is unsupported.



.. py:function:: convert_distance(value: float, unit_from: str, unit_to: str) -> float

   Converts distance values between metric and imperial units.

   Args:
       value (float): Input distance value.
       from_type (str): Original unit.
       to_type (str): Target unit.

   Returns:
       float: Converted distance value.

   Raises:
       ValueError: If unit is unsupported.



.. py:function:: _norm_temp_unit(unit: str) -> str

.. py:function:: _to_celsius(value: float, unit_from: str) -> float

.. py:function:: _from_celsius(c: float, unit_to: str) -> float

.. py:function:: convert_temperature(value: float, unit_from: str, unit_to: str) -> float

   Converts temperature between different scales.

   Args:
       value (float): Input temperature value.
       unit_from (str): Original unit. Supported: C, F, K (also °C, °F, °K).
       unit_to (str): Target unit. Supported: C, F, K (also °C, °F, °K).

   Returns:
       float: Converted temperature value (rounded to 3 decimals).

   Raises:
       ValueError: If unit is unsupported or Kelvin is invalid (< 0).



.. py:function:: format_temperature(value: float, unit: str, decimals: int = 1, symbol: bool = True) -> str

   Formats a temperature value with unit, e.g. '23.5 °C' or '296.6 K'.

   Args:
       value (float): Temperature value.
       unit (str): Unit to display (C, F, K).
       decimals (int): Decimal places.
       symbol (bool): If True, uses °C/°F, and K without degree symbol.

   Returns:
       str: Formatted temperature string.


