import ee
import geopandas as gpd
import pandas as pd
from typing import Tuple, Dict, Any, Optional
from .builder import (
    ReducerName,
    Frequency,
    ee_initialized,
    gdf_to_ee_geometry,

    _PRODUCT_REGISTRY,
    _build_vegetation,

    _norm_sat,
    _build_chirps,
    _build_lst,
    _compute,
    _empty,
    _advance_end,
    _dates_for_frequency,
    _timeseries_to_df,
    _compute_img,
    _period_dates,
    _build_period_img,
)



# ----------------------------
# ONE public entry function
# ----------------------------

def get_satellite_collection(
        product, 
        satellite=None, 
        start_date=None, 
        end_date=None,
    ):
    
    product = _norm_sat(product)

    if product not in _PRODUCT_REGISTRY:
        raise ValueError(f"Unsupported product: {product}")

    pipeline = _PRODUCT_REGISTRY[product]

    if pipeline == "vegetation":
        ic, meta = _build_vegetation(product, satellite, start_date, end_date)

    elif pipeline == "lst":
        ic, meta = _build_lst(satellite, start_date, end_date)

    elif pipeline == "chirps":
        ic, meta = _build_chirps(start_date, end_date)

    else:
        raise ValueError("Invalid pipeline")
    
    meta.update({
        "product": product,
        "satellite": satellite,
        "start_date": start_date,
        "end_date": end_date,
    })

    return ic, meta




# ------------------------------------
# ONE Compute period feature function
# ------------------------------------

def compute_period_feature(
    product: str,
    start: ee.Date,
    collection: ee.ImageCollection,
    geometry: ee.Geometry,
    frequency: str,
    meta: Dict[str, Any],
    scale: Optional[int] = None,
    ) -> ee.Feature:
    
    start = ee.Date(start)
    end = _advance_end(start, frequency)

    prod = product.upper()

    if scale is None:
        scale = int(meta.get("scale_m"))

    period_ic = collection.filterDate(start, end)
    size = period_ic.size()
    computed = _compute(prod, start, period_ic, geometry, scale, meta)
    empty = _empty(prod, start)

    return ee.Feature(ee.Algorithms.If(size.gt(0), computed, empty))



# ------------------------------------
# ONE Ccompute_timeseries function
# ------------------------------------

def compute_timeseries(
    product: str,
    start_date: str,
    end_date: str,
    frequency: str,
    roi_gdf: gpd.GeoDataFrame,
    satellite: Optional[str] = None,
    scale: Optional[int] = None,
    ) -> pd.DataFrame:
    
    ee_initialized()
    if roi_gdf is None:
        raise ValueError("Provide roi_gdf (Region of Interest)")

    geometry = gdf_to_ee_geometry(roi_gdf)

    ic, meta = get_satellite_collection(
        product=product,
        start_date=start_date,
        end_date=end_date,
        satellite=satellite,
        roi_gdf=roi_gdf,
    )

    dates = _dates_for_frequency(start_date, end_date, frequency)

    fc = ee.FeatureCollection(
        dates.map(lambda d: compute_period_feature(
            start=ee.Date(d),
            product=product,
            collection=ic,
            geometry=geometry,
            frequency=frequency,
            meta=meta,
            scale=scale,
        ))
    )

    df = _timeseries_to_df(fc)

    prod = product.upper()

    if prod == "LST":
        if "mean" in df.columns:
            df = df[df["mean"].notna()]

    elif prod == "CHIRPS":
        if "precipitation_mm" in df.columns:
            df = df[df["precipitation_mm"].notna()]

    elif prod in ("NDVI", "EVI"):
        key = prod.lower()
        if key in df.columns:
            df = df[df[key].notna()]

    elif prod == "NDVI_EVI":
        cols = [c for c in ("ndvi", "evi") if c in df.columns]
        if cols:
            df = df[df[cols].notna().any(axis=1)]

    if frequency.lower() == "monthly" and "date" in df.columns:
        df["month"] = pd.to_datetime(df["date"]).dt.strftime("%B")

    return df.reset_index(drop=True)



# ------------------------------------
# ONE get_product_image function
# ------------------------------------
def get_product_image(
    product: str,
    start_date: str,
    end_date: str,
    satellite: Optional[str] = None,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
    ) -> ee.Image:
    """
    Generates a single composite Earth Engine Image for a specific environmental product.

    This function creates a reduced composite image over a specified date range and 
    optional region of interest. It handles product-specific scaling (e.g., Kelvin to 
    Celsius for LST), projection transformations for MODIS data, and reducer logic.

    This function:
    - Initializes the Earth Engine session via `ee_initialized()`.
    - Converts the input `roi_gdf` to an `ee.Geometry` if provided.
    - Retrieves the source `ee.ImageCollection` and metadata via `get_satellite_collection`.
    - Applies projection transformation to the ROI if the satellite is MODIS.
    - Filters the collection to bounds of the ROI (if provided).
    - Validates that band information exists in the metadata.
    - Computes the final composite image using `_compute_img` with the specified reducer.
    - Returns product-specific units (e.g., °C for LST, mm for CHIRPS sum).

    Args:
        product (str): The environmental product identifier (e.g., "LST", "NDVI", "CHIRPS").
        start_date (str): Start date for the composite window in 'YYYY-MM-DD' format.
        end_date (str): End date for the composite window in 'YYYY-MM-DD' format.
        satellite (str, optional): Satellite platform identifier (e.g., "MODIS", "Landsat8"). 
            Required for certain products. Defaults to None.
        roi_gdf (gpd.GeoDataFrame, optional): The Region of Interest as a GeoDataFrame. 
            If provided, the image reduction is clipped/masked to this geometry. 
            Defaults to None.
        reducer (ReducerName, optional): The statistical reducer to apply over the time range. 
            Options include "mean", "median", "sum", "min", "max". 
            Note: "sum" is recommended for CHIRPS precipitation totals. 
            Defaults to "mean".

    Returns:
        ee.Image:
            A single-band or multi-band Earth Engine Image representing the composite.
            - **LST**: Returns temperature in degrees Celsius (°C).
            - **NDVI/EVI**: Returns vegetation index values (typically -1 to 1).
            - **CHIRPS**: Returns precipitation in millimeters (mm). 
              If `reducer="sum"`, returns total accumulation; otherwise returns daily statistic.

    Raises:
        ValueError: If the metadata does not contain required band information 
            ('bands' or 'band' keys missing).

    Notes:
        - **Earth Engine Initialization:** Calls `ee_initialized()` internally.
        - **MODIS Projection:** Automatically transforms the ROI geometry to match 
          the MODIS projection if applicable to ensure accurate pixel alignment.
        - **Scaling:** Product-specific scaling factors (e.g., LST Kelvin conversion) 
          are applied within `_compute_img` based on metadata.
        - **Reducer Logic:** For precipitation (CHIRPS), use `reducer="sum"` to get 
          total accumulation over the period. For vegetation/temperature, "mean" 
          is typically preferred.
    """
    ee_initialized()

    roi = gdf_to_ee_geometry(roi_gdf) if roi_gdf is not None else None

    ic, meta = get_satellite_collection(
        product=product,
        start_date=start_date,
        end_date=end_date,
        satellite=satellite,
        roi_gdf=roi_gdf,

    )
    if roi is not None and str(meta.get("satellite", "")).upper() == "MODIS":
        first = ee.Image(ic.first())
        b0 = (meta.get("bands") or [meta.get("band")])[0]
        proj = first.select(b0).projection()
        roi = roi.transform(proj, 1)

    if roi is not None:
        ic = ic.filterBounds(roi)

    prod = str(meta.get("product", product)).upper()
    bands = meta.get("bands") or ([meta.get("band")] if meta.get("band") else [])
    if not bands:
        raise ValueError("meta must include 'bands' or 'band'")

    r = reducer.lower()

    img = _compute_img(product, start_date, end_date, ic, meta, roi, r)

    return img



def get_product_image_collection(
    product: str,
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    satellite: Optional[str] = None,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
    ) -> ee.ImageCollection:
    """
    Generates a time-series Earth Engine ImageCollection of composite images.

    This function creates a sequence of reduced composite images (e.g., monthly mean NDVI) 
    over a specified date range. Each image in the collection represents a specific time 
    period (frequency) with statistics calculated over the optional Region of Interest (ROI).

    This function:
    - Initializes the Earth Engine session via `ee_initialized()`.
    - Converts the input `roi_gdf` to an `ee.Geometry` if provided.
    - Retrieves the source `ee.ImageCollection` and metadata via `get_satellite_collection`.
    - Validates the `reducer` parameter based on product type (e.g., allows "sum" for CHIRPS).
    - Applies projection transformation to the ROI if the satellite is MODIS.
    - Generates a sequence of timestamps based on `frequency` and `step_days`.
    - Maps `_build_period_img` over each period to construct individual composite images.
    - Sorts the resulting collection by `system:time_start`.
    - Adds a "month" property (string) to each image if frequency is "monthly".

    Args:
        product (str): The environmental product identifier (e.g., "LST", "NDVI", "CHIRPS").
        start_date (str): Start date for the time series in 'YYYY-MM-DD' format.
        end_date (str): End date for the time series in 'YYYY-MM-DD' format.
        frequency (Frequency, optional): Temporal resolution for the collection. 
            Options include "daily", "monthly", "yearly". Defaults to "monthly".
        satellite (str, optional): Satellite platform identifier (e.g., "MODIS", "Landsat8"). 
            Required for certain products. Defaults to None.
        roi_gdf (gpd.GeoDataFrame, optional): The Region of Interest as a GeoDataFrame. 
            If provided, images are reduced/clipped to this geometry. Defaults to None.
        reducer (ReducerName, optional): Statistical reducer to apply per period. 
            - For CHIRPS: "sum", "mean", "median", "min", "max".
            - For others (LST, NDVI, etc.): "mean", "median", "min", "max".
            Defaults to "mean".

    Returns:
        ee.ImageCollection:
            A collection of composite images sorted by time.
            - Each image represents one time period (e.g., one month).
            - Images contain reduced band values (e.g., mean NDVI per month).
            - Includes `system:time_start` property.
            - Includes "month" property (e.g., "January") if frequency is "monthly".

    Raises:
        ValueError:
            - If an invalid `reducer` is selected for the specific product 
              (e.g., "sum" is not allowed for NDVI).
            - If metadata is missing required band information (raised by downstream functions).

    Notes:
        - **Earth Engine Initialization:** Calls `ee_initialized()` internally.
        - **MODIS Projection:** Automatically transforms ROI geometry to match MODIS 
          projection if applicable to ensure accurate pixel alignment.
        - **CHIRPS Reduction:** Use `reducer="sum"` for precipitation totals over the period. 
          Use "mean" for daily average rates.
        - **Server-Side Mapping:** The loop over dates is executed server-side using 
          `ee.List.map`, ensuring scalability for long time series.
        - **Frequency Step:** The exact step size (days) is determined by `_period_dates` 
          based on the `frequency` argument.
    """
    ee_initialized()

    roi = gdf_to_ee_geometry(roi_gdf) if roi_gdf is not None else None

    ic, meta = get_satellite_collection(product, start_date, end_date, satellite=satellite)
    prod = str(meta.get("product", product)).upper()

    freq, step_days = _period_dates(start_date, end_date, frequency)
    r = reducer.lower()

    if prod == "CHIRPS":
        if r not in ("sum", "mean", "median", "min", "max"):
            raise ValueError("CHIRPS reducer must be one of: sum, mean, median, min, max")
    else:
        if r not in ("mean", "median", "min", "max"):
            raise ValueError(f"{prod} reducer must be one of: mean, median, min, max")

    if meta.get("product") in ("NDVI", "EVI") and str(meta.get("satellite", "")).upper() == "MODIS":
      first = ee.Image(ic.first())
      proj = first.select(meta["bands"][0]).projection()
      geometry = roi.transform(proj, 1)
      ic = ic.filterBounds(geometry)

    dates = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        step_days * 24 * 60 * 60 * 1000,
    )

    def _one_period(d):
        start = ee.Date(d)
        end = _advance_end(start, freq)
        period_ic = ic.filterDate(start, end)

        meta2 = ee.Dictionary(meta).set("frequency", freq)

        img = _build_period_img(
            prod=prod,
            r=r,
            start=start,
            end=end,
            period_ic=period_ic,
            meta={**meta, "frequency": freq},
            roi=roi,
        )
        return img

    img_coll = ee.ImageCollection(dates.map(_one_period)).sort("system:time_start")

    if freq == "monthly":
        img_coll = img_coll.map(lambda img: img.set({
            "month": ee.Date(img.get("system:time_start")).format("MMMM")
        }))

    return img_coll







