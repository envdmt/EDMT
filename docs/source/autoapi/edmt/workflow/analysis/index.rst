edmt.workflow.analysis
======================

.. py:module:: edmt.workflow.analysis






Module Contents
---------------

.. py:function:: create_ROI(latitude: float, longitude: float, extent_km: float = 100.0, name: str = 'AOI') -> geopandas.GeoDataFrame

   Create a square bounding box polygon centered on a WGS84 coordinate.

   Parameters
   ----------
   latitude : float
       Center latitude in decimal degrees (WGS84 / EPSG:4326).
   longitude : float
       Center longitude in decimal degrees (WGS84 / EPSG:4326).
   extent_km : float, optional
       Full side length of the bounding box in kilometres (default: 100).
       e.g. 10 → 10 km × 10 km box centered on the coordinate.
   name : str, optional
       Label for the polygon feature (default: "AOI").

   Returns
   -------
   gpd.GeoDataFrame
       Single-row GeoDataFrame (EPSG:4326) with columns:
       name, latitude, longitude, extent_km, geometry.

   Notes
   -----
   Degree-to-metre conversion uses the WGS84 approximation:
       1° latitude  ≈ 111 320 m  (constant)
       1° longitude ≈ 111 320 × cos(lat) m  (varies with latitude)


.. py:data:: NDVI_WET_THRESHOLD
   :type:  float
   :value: 0.5


.. py:function:: _otsu_threshold(values: numpy.ndarray) -> float

   1-D Otsu's method: find the cut-point that maximises
   between-class variance in `values`.


.. py:function:: _minmax_normalize_fixed(series: pandas.Series, scale_min: float, scale_max: float) -> pandas.Series

   Rescale a Series to [0, 1] using a *fixed* global range instead of
   the data's own min/max.  Values outside [scale_min, scale_max] are
   clipped before normalisation.

   Using fixed bounds prevents the pathological amplification that occurs
   when all data values occupy a very narrow band (e.g. NDVI 0.094–0.101
   treated as if it spans the full 0–1 range).


.. py:function:: _aggregate_to_monthly(df: pandas.DataFrame, date_col: str, value_col: str, agg_func: str, out_col: str) -> pandas.DataFrame

   Parse dates, extract year/month, and aggregate value_col.


.. py:function:: classify_ndvi_seasons(df: pandas.DataFrame, date_col: str = 'date', ndvi_col: str = 'ndvi', threshold: float = None, threshold_method: str = 'discrete', wet_label: str = 'Wet', dry_label: str = 'Dry', agg_func: str = 'mean') -> pandas.DataFrame

   Aggregate NDVI observations to monthly means and classify each
   month as a wet or dry period based on a vegetation threshold.

   Parameters
   ----------
   df : pd.DataFrame
       Input DataFrame containing at minimum a date and NDVI column.
   date_col : str, optional
       Name of the date column (default: "date").
   ndvi_col : str, optional
       Name of the NDVI column (default: "ndvi").
   threshold : float, optional
       Explicit NDVI cut-off on the true -1 to +1 scale.
       Overrides `threshold_method` when supplied.
       Months with mean NDVI >= threshold → wet; below → dry.
       
   threshold_method : str, optional
       Auto-threshold strategy used when `threshold` is None:

       "discrete" – Ecological fixed threshold from the NDVI scale
                    (NDVI_WET_THRESHOLD = 0.25 by default).
                    **Recommended** — anchors the result to real-world
                    vegetation meaning regardless of data range. (default)
       "otsu"     – Maximises between-class variance within the data.
                    Only meaningful when the data spans a wide dynamic
                    range (e.g. > 0.15 spread). Avoid for narrow-band data.
       "median"   – Median of monthly means.
       "mean"     – Mean of monthly means.

   wet_label : str, optional
       Label for wet months (default: "Wet").
   dry_label : str, optional
       Label for dry months (default: "Dry").
   agg_func : str, optional
       Aggregation function applied per month:
       "mean" | "median" | "max" (default: "mean").

   Returns
   -------
   pd.DataFrame
       Monthly DataFrame ordered chronologically with columns:
       year, month, month_name, ndvi_mean, threshold, season,
       ndvi_vegetation_class.

       ndvi_vegetation_class  →  human-readable land-cover interpretation
       derived from the true NDVI scale (independent of the wet/dry split).

   Notes
   -----
   The "discrete" method (default) anchors classification to the actual
   NDVI scale (-1 to +1).  Statistical methods (otsu/median/mean) find a
   threshold *within* the observed data range, which can produce misleading
   results when all values are clustered in a narrow band — e.g. labelling
   a month as "Wet" simply because its NDVI is 0.001 above the rest, even
   though 0.10 is objectively bare soil by any vegetation index standard.


.. py:data:: _DEFAULT_SEASON_LABELS
   :type:  List[str]
   :value: ['Dry Season', 'Dry-Wet Transition', 'Rainfall Onset', 'Wet Season', 'Rainy Season']


.. py:data:: _WET_LABELS

.. py:data:: _TRANSITION_LABEL
   :value: 'Dry-Wet Transition'


.. py:data:: _DRY_LABEL
   :value: 'Dry Season'


.. py:function:: _minmax_normalize(series: pandas.Series) -> pandas.Series

   Rescale a Series to [0, 1]. Returns 0.5 if all values are identical.


.. py:function:: _aggregate_to_monthly(df: pandas.DataFrame, date_col: str, value_col: str, agg_func: str, out_col: str) -> pandas.DataFrame

   Parse dates, extract year/month, and aggregate value_col.


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

   Parameters
   ----------
   df_ndvi : pd.DataFrame
       16-day or finer NDVI observations (aggregated to monthly mean).
   df_rainfall : pd.DataFrame
       Weekly or finer precipitation observations (aggregated to monthly sum).
   df_lst : pd.DataFrame
       Monthly or finer LST observations (aggregated to monthly mean).
   ndvi_date_col : str
       Date column in df_ndvi (default: "date").
   ndvi_col : str
       NDVI value column (default: "ndvi").
   rainfall_date_col : str
       Date column in df_rainfall (default: "date").
   rainfall_col : str
       Precipitation column (default: "precipitation_mm").
   lst_date_col : str
       Date column in df_lst (default: "date").
   lst_col : str
       LST value column (default: "mean").
   weights : tuple of 3 floats
       Relative importance of (rainfall, ndvi, temperature). Must sum to 1.0
       (default: 0.40, 0.35, 0.25).
   category_labels : list of 5 str, optional
       Custom season names ordered driest → wettest.
   rainfall_gate_mm : float, optional
       Monthly rainfall (mm) below which a month is forced to "Dry Season",
       regardless of NDVI or LST (default: 1.0 mm).
   transition_gate_mm : float, optional
       Monthly rainfall (mm) below which a month is capped at
       "Dry-Wet Transition" if the score would place it in a wetter
       category (default: 5.0 mm).

   Returns
   -------
   pd.DataFrame
       Chronologically sorted monthly DataFrame with columns:
       year, month, month_name, rainfall_mm, ndvi_mean, lst_mean,
       composite_score, season, season_source.

       season_source: "score" if the label came from the composite score,
                      "rainfall_gate" if it was overridden.


