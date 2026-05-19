import math
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List



def create_ROI(
    latitude: float,
    longitude: float,
    extent_km: float = 100.0,
    name: str = "AOI",
    ) -> gpd.GeoDataFrame:
    """
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
    """
    _KM_TO_M: float = 1_000.0
    extent_m: float = extent_km * _KM_TO_M
 
    _METRES_PER_DEGREE_LAT: float = 111_320.0
    metres_per_degree_lon: float = _METRES_PER_DEGREE_LAT * math.cos(
        math.radians(latitude)
    )

    half_extent_m: float = extent_m / 2.0
    delta_lat: float = half_extent_m / _METRES_PER_DEGREE_LAT
    delta_lon: float = half_extent_m / metres_per_degree_lon

    west: float  = longitude - delta_lon
    east: float  = longitude + delta_lon
    south: float = latitude  - delta_lat
    north: float = latitude  + delta_lat

    bbox_geom = box(west, south, east, north)

    return gpd.GeoDataFrame(
        {
            "name":       [name],
            "latitude":   [latitude],
            "longitude":  [longitude],
            "extent_km":  [extent_km],
            "geometry":   [bbox_geom],
        },
        crs="EPSG:4326",
    )



def _otsu_threshold(values: np.ndarray) -> float:
    """
    1-D Otsu's method: find the cut-point that maximises
    between-class variance in `values`.
    """
    sorted_vals = np.sort(values)
    best_thresh = sorted_vals[0]
    best_var = -np.inf

    for t in sorted_vals[1:]:
        below = values[values < t]
        above = values[values >= t]

        if len(below) == 0 or len(above) == 0:
            continue

        w0, w1 = len(below) / len(values), len(above) / len(values)
        between_var = w0 * w1 * (below.mean() - above.mean()) ** 2

        if between_var > best_var:
            best_var = between_var
            best_thresh = float(t)

    return best_thresh


def classify_ndvi_seasons(
    df: pd.DataFrame,
    date_col: str = "date",
    ndvi_col: str = "ndvi",
    threshold: float = None,
    threshold_method: str = "otsu",
    wet_label: str = "Wet",
    dry_label: str = "Dry",
    agg_func: str = "mean",
) -> pd.DataFrame:
    """
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
        Explicit NDVI cut-off. Overrides `threshold_method` when supplied.
        Months with mean NDVI >= threshold → wet; below → dry.
    threshold_method : str, optional
        Auto-threshold strategy used when `threshold` is None:

        "otsu"   – Maximises between-class variance (default).
                   Best for global / mixed biomes; handles unequal
                   season lengths and skewed distributions.
        "median" – Median of monthly means.
                   Good when wet and dry months are roughly equal in number.
        "mean"   – Mean of monthly means.
                   Sensitive to outlier months; use only on clean data.

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
        year, month, month_name, ndvi_mean, threshold, season.
    """
    if date_col not in df.columns:
        raise KeyError(f"Date column '{date_col}' not found in DataFrame.")
    if ndvi_col not in df.columns:
        raise KeyError(f"NDVI column '{ndvi_col}' not found in DataFrame.")

    _VALID_AGG = {"mean", "median", "max"}
    if agg_func not in _VALID_AGG:
        raise ValueError(f"agg_func must be one of {_VALID_AGG}, got '{agg_func}'.")

    _VALID_METHODS = {"otsu", "median", "mean"}
    if threshold_method not in _VALID_METHODS:
        raise ValueError(
            f"threshold_method must be one of {_VALID_METHODS}, "
            f"got '{threshold_method}'."
        )

    work = df[[date_col, ndvi_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col])
    work["year"]  = work[date_col].dt.year
    work["month"] = work[date_col].dt.month

    monthly: pd.DataFrame = (
        work.groupby(["year", "month"])[ndvi_col]
        .agg(agg_func)
        .reset_index()
        .rename(columns={ndvi_col: "ndvi_mean"})
    )

    monthly["_period"] = pd.to_datetime(monthly[["year", "month"]].assign(day=1))
    monthly = monthly.sort_values("_period").reset_index(drop=True)
    monthly = monthly.drop(columns="_period")

    monthly.insert(
        2,
        "month_name",
        pd.to_datetime(monthly["month"], format="%m").dt.strftime("%B"),
    )

    if threshold is not None:
        resolved_threshold = float(threshold)
    else:
        values = monthly["ndvi_mean"].to_numpy()
        if threshold_method == "otsu":
            resolved_threshold = _otsu_threshold(values)
        elif threshold_method == "median":
            resolved_threshold = float(np.median(values))
        else:  # mean
            resolved_threshold = float(np.mean(values))

    monthly["threshold"] = round(resolved_threshold, 6)
    monthly["season"] = np.where(
        monthly["ndvi_mean"] >= resolved_threshold, wet_label, dry_label
    )
    return monthly


_DEFAULT_SEASON_LABELS: List[str] = [
    "Dry Season",
    "Dry-Wet Transition",
    "Rainfall Onset",
    "Wet Season",
    "Rainy Season",
]

_WET_LABELS = {"Rainy Season", "Wet Season", "Rainfall Onset"}
_TRANSITION_LABEL = "Dry-Wet Transition"
_DRY_LABEL = "Dry Season"


def _minmax_normalize(series: pd.Series) -> pd.Series:
    """Rescale a Series to [0, 1]. Returns 0.5 if all values are identical."""
    s_min, s_max = series.min(), series.max()
    if s_max == s_min:
        return pd.Series(0.5, index=series.index)
    return (series - s_min) / (s_max - s_min)


def _aggregate_to_monthly(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    agg_func: str,
    out_col: str,
) -> pd.DataFrame:
    """Parse dates, extract year/month, and aggregate value_col."""
    work = df[[date_col, value_col]].copy()
    work[date_col] = pd.to_datetime(work[date_col])
    work["year"]  = work[date_col].dt.year
    work["month"] = work[date_col].dt.month
    monthly = (
        work.groupby(["year", "month"])[value_col]
        .agg(agg_func)
        .reset_index()
        .rename(columns={value_col: out_col})
    )
    return monthly



def classify_climate_seasons(
    df_ndvi: pd.DataFrame,
    df_rainfall: pd.DataFrame,
    df_lst: pd.DataFrame,
    ndvi_date_col: str = "date",
    ndvi_col: str = "ndvi",
    rainfall_date_col: str = "date",
    rainfall_col: str = "precipitation_mm",
    lst_date_col: str = "date",
    lst_col: str = "mean",
    weights: Tuple[float, float, float] = (0.40, 0.35, 0.25),
    category_labels: Optional[List[str]] = None,
    rainfall_gate_mm: float = 1.0,    
    transition_gate_mm: float = 15.0,  
) -> pd.DataFrame:
    """
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
    """
    if rainfall_gate_mm > transition_gate_mm:
        raise ValueError(
            f"rainfall_gate_mm ({rainfall_gate_mm}) must be ≤ "
            f"transition_gate_mm ({transition_gate_mm})."
        )

    w_rain, w_ndvi, w_temp = weights
    if not abs(sum(weights) - 1.0) < 1e-6:
        raise ValueError(
            f"weights must sum to 1.0, got {sum(weights):.4f}. "
            f"Received: rainfall={w_rain}, ndvi={w_ndvi}, temperature={w_temp}."
        )

    labels = category_labels or _DEFAULT_SEASON_LABELS
    if len(labels) != 5:
        raise ValueError(
            f"category_labels must contain exactly 5 labels, got {len(labels)}."
        )

    dry_label        = labels[0] 
    transition_label = labels[1] 
    wet_labels       = set(labels[2:]) 

    monthly_rainfall = _aggregate_to_monthly(
        df_rainfall, rainfall_date_col, rainfall_col, "sum", "rainfall_mm"
    )
    monthly_ndvi = _aggregate_to_monthly(
        df_ndvi, ndvi_date_col, ndvi_col, "mean", "ndvi_mean"
    )
    monthly_lst = _aggregate_to_monthly(
        df_lst, lst_date_col, lst_col, "mean", "lst_mean"
    )

    merged = (
        monthly_rainfall
        .merge(monthly_ndvi, on=["year", "month"], how="inner")
        .merge(monthly_lst,  on=["year", "month"], how="inner")
    )

    merged["_period"] = pd.to_datetime(merged[["year", "month"]].assign(day=1))
    merged = merged.sort_values("_period").reset_index(drop=True)
    merged.insert(2, "month_name", merged["_period"].dt.strftime("%B"))
    merged = merged.drop(columns="_period")

    merged["_rain_norm"] = _minmax_normalize(merged["rainfall_mm"])
    merged["_ndvi_norm"] = _minmax_normalize(merged["ndvi_mean"])
    merged["_temp_norm"] = _minmax_normalize(merged["lst_mean"])

    merged["composite_score"] = (
        w_rain * merged["_rain_norm"]
        + w_ndvi * merged["_ndvi_norm"]
        + w_temp * (1 - merged["_temp_norm"])
    ).round(4)

    merged = merged.drop(columns=["_rain_norm", "_ndvi_norm", "_temp_norm"])

    merged["season"] = pd.cut(
        merged["composite_score"],
        bins=5,
        labels=labels,
        include_lowest=True,
    ).astype(str)

    merged["season_source"] = "score"

    transition_mask = (
        (merged["rainfall_mm"] < transition_gate_mm) &
        (merged["rainfall_mm"] >= rainfall_gate_mm) &
        (merged["season"].isin(wet_labels))
    )
    merged.loc[transition_mask, "season"]        = transition_label
    merged.loc[transition_mask, "season_source"] = "rainfall_gate"

    dry_mask = merged["rainfall_mm"] < rainfall_gate_mm
    merged.loc[dry_mask, "season"]        = dry_label
    merged.loc[dry_mask, "season_source"] = "rainfall_gate"

    return merged[[
        "year", "month", "month_name",
        "rainfall_mm", "ndvi_mean", "lst_mean",
        "composite_score", "season", "season_source",
    ]]



