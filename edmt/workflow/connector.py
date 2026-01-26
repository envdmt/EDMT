import ee
import geopandas as gpd
import pandas as pd
from typing import Tuple, Dict, Any, Optional
from .builder import (
    ReducerName,
    Frequency,
    ee_initialized,
    gdf_to_ee_geometry,
    _norm,
    _build_chirps,
    _build_lst,
    _build_ndvi,
    _build_evi,
    _build_ndvi_evi,
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
    product: str,
    start_date: str,
    end_date: str,
    satellite: Optional[str] = None,
) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    """
    Single workflow entry-point for satellite/environment collections.

    Parameters
    ----------
    product : str
        One of: "LST", "NDVI", "EVI", "NDVI_EVI", "CHIRPS"
    start_date, end_date : str
        Date range in 'YYYY-MM-DD'
    satellite : str, optional
        Required for: LST, NDVI, EVI, NDVI_EVI
        Ignored for: CHIRPS

    Returns
    -------
    (ic, meta)
      ic   : ee.ImageCollection
      meta : dict with bands, units, scale, scaling factors (when relevant)
    """
    prod = _norm(product)

    if prod == "CHIRPS":
        return _build_chirps(start_date, end_date)

    if not satellite:
        raise ValueError(f"'satellite' is required for product={product} (except CHIRPS).")

    if prod == "LST":
        return _build_lst(satellite, start_date, end_date)

    if prod == "NDVI":
        return _build_ndvi(satellite, start_date, end_date)

    if prod == "EVI":
        return _build_evi(satellite, start_date, end_date)

    if prod in ("NDVI_EVI", "NDVI+EVI", "NDVIAND_EVI"):
        return _build_ndvi_evi(satellite, start_date, end_date)

    raise ValueError(f"Unsupported product: {product}. Use LST, NDVI, EVI, NDVI_EVI, or CHIRPS.")



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
    """
    ONE feature builder for ALL products.

    Uses:
      - meta["bands"] or meta["band"]
      - meta["scale_m"] default scale
      - meta["unit"] optional unit label
      - meta["multiply"]/meta["add"] for LST scaling if you want it inside here (optional)
    """
    start = ee.Date(start)
    end = _advance_end(start, frequency)

    prod = product.upper()

    if scale is None:
        scale = int(meta.get("scale_m"))

    period_ic = collection.filterDate(start, end)
    computed = _compute(prod, start, period_ic, geometry, scale, meta)
    empty = _empty(prod, start)

    return ee.Feature(ee.Algorithms.If(period_ic.size().gt(0), computed, empty))



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
    ee_initialized()  # your helper
    if roi_gdf is None:
        raise ValueError("Provide roi_gdf (Region of Interest)")

    geometry = gdf_to_ee_geometry(roi_gdf)

    ic, meta = get_satellite_collection(
        product=product,
        start_date=start_date,
        end_date=end_date,
        satellite=satellite,
    )

    if satellite:
        meta = {**meta, "satellite": satellite.upper()}

    if meta.get("product") in ("NDVI", "EVI") and str(meta.get("satellite", "")).upper() == "MODIS":
      first = ee.Image(ic.first())
      proj = first.select(meta["bands"][0]).projection()
      geometry = geometry.transform(proj, 1)

    ic = ic.filterBounds(geometry)

    dates = _dates_for_frequency(start_date, end_date, frequency)

    fc = ee.FeatureCollection(
        dates.map(lambda d: compute_period_feature(
            product=product,
            start=ee.Date(d),
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
    Returns a single composite image for product in the date window.

    - LST: returns °C (expects meta has multiply/add or unit K/°C)
    - NDVI/EVI: returns index [-1,1]
    - CHIRPS: for reducer='sum' returns total mm; otherwise daily statistic
    """
    ee_initialized()

    roi = gdf_to_ee_geometry(roi_gdf) if roi_gdf is not None else None

    ic, meta = get_satellite_collection(product, start_date, end_date, satellite=satellite)

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







