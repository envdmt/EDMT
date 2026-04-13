import ee
import geopandas as gpd
import pandas as pd
from typing import Dict, Any, Optional,Literal

from .builder import (
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
    _freq_unit,
    _timeseries_to_df,
    _composite_image,
    _build_period_img,
)

ReducerName = Literal["mean", "median", "sum", "min", "max"]

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
# ONE Compute_timeseries function
# ------------------------------------

def ComputeTimeseries(
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
    )

    if satellite and satellite.upper() == "MODIS":
        bands = meta.get("bands", []) or [meta.get("band")]
        band = bands[0] if bands else None
        if band:
            first = ee.Image(ic.first())
            proj = first.select(band).projection()
            geometry = geometry.transform(proj, 1)

    ic = ic.filterBounds(geometry)

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
# ONE CompositeImage function
# ------------------------------------


def CompositeImage(
    product,
    start_date,
    end_date,
    satellite=None,
    roi_gdf=None,
    reducer="mean"
):
    product = _norm_sat(product)

    ee_initialized()

    roi = gdf_to_ee_geometry(roi_gdf) if roi_gdf is not None else None

    ic, meta = get_satellite_collection(
        product=product,
        start_date=start_date,
        end_date=end_date,
        satellite=satellite,
    )

    start = ee.Date(start_date)
    end = ee.Date(end_date)

    img = _composite_image(
        product=product,
        start=start,
        end=end,
        period_ic=ic,
        meta=meta,
        reducer=reducer.lower(),
    )

    if roi is not None:
        img = img.clip(roi)

    return img



def CollectionImage(
    product: str,
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    satellite: Optional[str] = None,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.ImageCollection:

    ee_initialized()

    product = _norm_sat(product)
    freq = _freq_unit(frequency)
    r = reducer.lower()

    roi = gdf_to_ee_geometry(roi_gdf) if roi_gdf is not None else None

    ic, meta = get_satellite_collection(
        product=product,
        start_date=start_date,
        end_date=end_date,
        satellite=satellite,
    )

    prod = product

    if prod == "CHIRPS":
        allowed = ("sum", "mean", "median", "min", "max")
    else:
        allowed = ("mean", "median", "min", "max")

    if r not in allowed:
        raise ValueError(f"{prod} reducer must be one of: {', '.join(allowed)}")

    if prod in ("NDVI", "EVI") and str(meta.get("satellite", "")).upper() == "MODIS" and roi is not None:
        first = ee.Image(ic.first())
        proj = first.select(meta["bands"][0]).projection()
        roi = roi.transform(proj, 1)
        ic = ic.filterBounds(roi)

    start = ee.Date(start_date)
    end = ee.Date(end_date)

    dates = _make_dates(start, end, freq)

    def _one_period(d):
        start = ee.Date(d)
        end = _advance_end(start, freq)

        period_ic = ic.filterDate(start, end)

        return _build_period_img(
            prod=prod,
            r=r,
            start=start,
            end=end,
            period_ic=period_ic,
            meta={**meta, "frequency": freq},
            roi=roi,
        )

    img_coll = ee.ImageCollection(dates.map(_one_period)).sort("system:time_start")

    if freq == "monthly":
        img_coll = img_coll.map(lambda img: img.set({
            "month": ee.Date(img.get("system:time_start")).format("MMMM")
        }))

    return img_coll







