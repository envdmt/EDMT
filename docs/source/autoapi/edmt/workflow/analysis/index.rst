edmt.workflow.analysis
======================

.. py:module:: edmt.workflow.analysis






Module Contents
---------------

.. py:function:: create_ROI(latitude: float, longitude: float, extent_km: float = 100.0, name: str = 'AOI') -> geopandas.GeoDataFrame

   Create a square bounding box polygon centered on a WGS84 coordinate.

   :param latitude: Center latitude in decimal degrees (WGS84 / EPSG:4326).
   :type latitude: float
   :param longitude: Center longitude in decimal degrees (WGS84 / EPSG:4326).
   :type longitude: float
   :param extent_km: Full side length of the bounding box in kilometres (default: 100).
                     e.g. 10 → 10 km × 10 km box centered on the coordinate.
   :type extent_km: float, optional
   :param name: Label for the polygon feature (default: "AOI").
   :type name: str, optional

   :returns: Single-row GeoDataFrame (EPSG:4326) with columns:
             name, latitude, longitude, extent_km, geometry.
   :rtype: gpd.GeoDataFrame

   .. rubric:: Notes

   Degree-to-metre conversion uses the WGS84 approximation:
       1° latitude  ≈ 111 320 m  (constant)
       1° longitude ≈ 111 320 × cos(lat) m  (varies with latitude)


.. py:data:: NDVI_WET_THRESHOLD
   :type:  float
   :value: 0.5


.. py:function:: classify_ndvi_seasons(df: pandas.DataFrame, date_col: str = 'date', ndvi_col: str = 'ndvi', threshold: float = None, threshold_method: str = 'discrete', wet_label: str = 'Wet', dry_label: str = 'Dry', agg_func: str = 'mean') -> pandas.DataFrame

   Aggregate NDVI observations to monthly means and classify each
   month as a wet or dry period based on a vegetation threshold.

   :param df: Input DataFrame containing at minimum a date and NDVI column.
   :type df: pd.DataFrame
   :param date_col: Name of the date column (default: "date").
   :type date_col: str, optional
   :param ndvi_col: Name of the NDVI column (default: "ndvi").
   :type ndvi_col: str, optional
   :param threshold: Explicit NDVI cut-off on the true -1 to +1 scale.
                     Overrides `threshold_method` when supplied.
                     Months with mean NDVI >= threshold → wet; below → dry.
   :type threshold: float, optional
   :param threshold_method: Auto-threshold strategy used when `threshold` is None:

                            "discrete" – Ecological fixed threshold from the NDVI scale
                                         (NDVI_WET_THRESHOLD = 0.25 by default).
                                         **Recommended** — anchors the result to real-world
                                         vegetation meaning regardless of data range. (default)
                            "otsu"     – Maximises between-class variance within the data.
                                         Only meaningful when the data spans a wide dynamic
                                         range (e.g. > 0.15 spread). Avoid for narrow-band data.
                            "median"   – Median of monthly means.
                            "mean"     – Mean of monthly means.
   :type threshold_method: str, optional
   :param wet_label: Label for wet months (default: "Wet").
   :type wet_label: str, optional
   :param dry_label: Label for dry months (default: "Dry").
   :type dry_label: str, optional
   :param agg_func: Aggregation function applied per month:
                    "mean" | "median" | "max" (default: "mean").
   :type agg_func: str, optional

   :returns: Monthly DataFrame ordered chronologically with columns:
             year, month, month_name, ndvi_mean, threshold, season,
             ndvi_vegetation_class.

             ndvi_vegetation_class  →  human-readable land-cover interpretation
             derived from the true NDVI scale (independent of the wet/dry split).
   :rtype: pd.DataFrame

   .. rubric:: Notes

   The "discrete" method (default) anchors classification to the actual
   NDVI scale (-1 to +1).  Statistical methods (otsu/median/mean) find a
   threshold *within* the observed data range, which can produce misleading
   results when all values are clustered in a narrow band — e.g. labelling
   a month as "Wet" simply because its NDVI is 0.001 above the rest, even
   though 0.10 is objectively bare soil by any vegetation index standard.


.. py:function:: classify_climate_seasons(df_ndvi: pandas.DataFrame, df_rainfall: pandas.DataFrame, df_lst: pandas.DataFrame, ndvi_date_col: str = 'date', ndvi_col: str = 'ndvi', rainfall_date_col: str = 'date', rainfall_col: str = 'precipitation_mm', lst_date_col: str = 'date', lst_col: str = 'mean', weights: Tuple[float, float, float] = (0.4, 0.35, 0.25), category_labels: Optional[List[str]] = None, rainfall_gate_mm: float = 1.0, transition_gate_mm: float = 15.0) -> pandas.DataFrame

   Merge monthly NDVI, rainfall, and LST data, then classify each month
   into one of five climate seasons using a normalised composite score.

   Composite score (0 = driest, 1 = wettest)
   ------------------------------------------
   score = w_rain  × rainfall_norm
         + w_ndvi  × ndvi_norm
         + w_temp  × (1 − temp_norm)   ← inverted: high temp → dry

   Rainfall gate (applied after scoring)
   --------------------------------------
   Prevents non-dry labels when rainfall is negligible, regardless of
   what NDVI or LST suggest:

     rainfall_mm < rainfall_gate_mm   → forced "Dry Season"
     rainfall_mm < transition_gate_mm → capped at "Dry-Wet Transition"
                                        (only if score-based label is wetter)

   :param df_ndvi: 16-day or finer NDVI observations (aggregated to monthly mean).
   :type df_ndvi: pd.DataFrame
   :param df_rainfall: Weekly or finer precipitation observations (aggregated to monthly sum).
   :type df_rainfall: pd.DataFrame
   :param df_lst: Monthly or finer LST observations (aggregated to monthly mean).
   :type df_lst: pd.DataFrame
   :param ndvi_date_col: Date column in df_ndvi (default: "date").
   :type ndvi_date_col: str
   :param ndvi_col: NDVI value column (default: "ndvi").
   :type ndvi_col: str
   :param rainfall_date_col: Date column in df_rainfall (default: "date").
   :type rainfall_date_col: str
   :param rainfall_col: Precipitation column (default: "precipitation_mm").
   :type rainfall_col: str
   :param lst_date_col: Date column in df_lst (default: "date").
   :type lst_date_col: str
   :param lst_col: LST value column (default: "mean").
   :type lst_col: str
   :param weights: Relative importance of (rainfall, ndvi, temperature). Must sum to 1.0
                   (default: 0.40, 0.35, 0.25).
   :type weights: tuple of 3 floats
   :param category_labels: Custom season names ordered driest → wettest.
   :type category_labels: list of 5 str, optional
   :param rainfall_gate_mm: Monthly rainfall (mm) below which a month is forced to "Dry Season",
                            regardless of NDVI or LST (default: 1.0 mm).
   :type rainfall_gate_mm: float, optional
   :param transition_gate_mm: Monthly rainfall (mm) below which a month is capped at
                              "Dry-Wet Transition" if the score would place it in a wetter
                              category (default: 5.0 mm).
   :type transition_gate_mm: float, optional

   :returns: Chronologically sorted monthly DataFrame with columns:
             year, month, month_name, rainfall_mm, ndvi_mean, lst_mean,
             composite_score, season, season_source.

             season_source: "score" if the label came from the composite score,
                            "rainfall_gate" if it was overridden.
   :rtype: pd.DataFrame


