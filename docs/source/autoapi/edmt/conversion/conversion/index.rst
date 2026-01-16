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

.. py:function:: sdf_to_gdf(sdf, crs=None)

   Converts a spatial DataFrame to a GeoDataFrame with optional CRS assignment.

   Args:
       sdf (pd.DataFrame): Input spatial DataFrame containing geometry column.
       crs (str or int, optional): Coordinate Reference System. Defaults to EPSG:4326.

   Returns:
       gpd.GeoDataFrame: A cleaned GeoDataFrame with valid geometries.

   Raises:
       ValueError: If input is not a DataFrame or is empty.



.. py:function:: generate_uuid(df, index=False)

   Adds a 'uuid' column to the DataFrame if no existing UUID-like column exists.

   Args:
       df (pd.DataFrame): The DataFrame to add UUIDs to.
       index (bool): Whether to set 'uuid' as the DataFrame index.

   Returns:
       pd.DataFrame: DataFrame with UUIDs added if needed.

   Raises:
       ValueError: If input is not a DataFrame or is empty.



.. py:function:: get_utm_epsg(longitude=None)

   Generates UTM EPSG code based on longitude.

   Args:
       longitude (float): Longitude value to determine UTM zone.

   Returns:
       str: EPSG code as a string.

   Raises:
       KeyError: If longitude is not provided.



.. py:function:: to_gdf(df)

   Converts a DataFrame with location data into a GeoDataFrame with point geometries.

   Args:
       df (pd.DataFrame): Input DataFrame with location data.

   Returns:
       gpd.GeoDataFrame: GeoDataFrame with point geometries.



.. py:function:: convert_time(time_value: float, unit_from: str, unit_to: str) -> float

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



.. py:function:: convert_distance(value: float, from_type: str, to_type: str) -> float

   Converts distance values between metric and imperial units.

   Args:
       value (float): Input distance value.
       from_type (str): Original unit.
       to_type (str): Target unit.

   Returns:
       float: Converted distance value.

   Raises:
       ValueError: If unit is unsupported.



