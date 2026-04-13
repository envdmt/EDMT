import ee
import geopandas as gpd
import pandas as pd
from typing import Dict, Any, Optional,Literal

from .builder import (
    Frequency,
    ReducerName,
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
    _make_dates,
    _timeseries_to_df,
    _composite_image,
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
    """
    Retrieve an Earth Engine ImageCollection and metadata for a supported environmental data product.

    This function serves as a unified entry point to access preconfigured satellite or gridded 
    datasets (e.g., NDVI, LST, precipitation) by delegating to specialized internal pipelines. 
    It returns both the raw image collection and a dictionary of processing parameters.

    Parameters
    ----------
    product : str
        Name of the environmental data product. Supported values include:
        - Vegetation indices: "NDVI", "EVI"
        - Land Surface Temperature: "LST"
        - Precipitation: "CHIRPS"
        (Case-insensitive; aliases are normalized internally.)
    satellite : str, optional
        Satellite platform or sensor (e.g., "MODIS", "LANDSAT", "SENTINEL2"). 
        Required for vegetation and LST products; ignored for grid-based products like CHIRPS.
    start_date : str, optional
        Start date in 'YYYY-MM-DD' format. Required if `end_date` is provided.
    end_date : str, optional
        End date in 'YYYY-MM-DD' format. Required if `start_date` is provided.

    Returns
    -------
    tuple[ee.ImageCollection, dict]
        - **ImageCollection**: Filtered and preprocessed Earth Engine image collection.
        - **meta**: Dictionary containing:
            - Product-specific scaling factors, band names, and units
            - Input arguments: `"product"`, `"satellite"`, `"start_date"`, `"end_date"`

    Raises
    ------
    ValueError
        If `product` is not supported or if required arguments are missing for the selected pipeline.

    Notes
    -----
    - Date filtering is applied during collection construction.
    - No cloud masking, quality filtering, or unit conversion is performed beyond what is 
      defined in the underlying pipeline.
    - All collections preserve native temporal and spatial metadata for downstream use.
    """
    
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
    """
    Compute spatial summary statistics for a given environmental product 
    over a time period and region of interest, returning an Earth Engine Feature.

    This function aggregates images in the input collection over a temporal window (defined by `start` 
    and `frequency`), computes statistics over `geometry`, and packages results into a feature with 
    standardized properties—including product-specific metadata from `meta`.

    Parameters
    ----------
    product : str
        Environmental product name (e.g., "NDVI", "LST", "CHIRPS"). Used to select appropriate 
        statistic computation logic.
    start : ee.Date
        Start date of the aggregation period.
    collection : ee.ImageCollection
        Pre-filtered ImageCollection containing the relevant band(s).
    geometry : ee.Geometry
        Region of interest for spatial reduction.
    frequency : {"daily", "weekly", "monthly", "yearly"}
        Temporal interval defining the period length. Determines end date.
    meta : dict
        Metadata dictionary (typically from `get_satellite_collection`) containing at least:
        - `"scale_m"`: default spatial resolution (in meters)
        - `"band"`: primary band name (e.g., "NDVI")
        - `"unit"`: measurement unit (e.g., "NDVI", "°C", "mm")
        Additional keys may be used by `_compute`.
    scale : int, optional
        Spatial resolution (in meters) for reduction. If omitted, defaults to `meta["scale_m"]`.

    Returns
    -------
    ee.Feature
        A feature with no geometry and the following properties:
        - `"date"`: Period start formatted as "YYYY-MM-dd"
        - `"product"`: Uppercase product name
        - `"band"`: Band name used (from `meta`)
        - `"unit"`: Unit of measurement (from `meta`)
        - `"n_images"`: Number of images in the period
        - Statistic keys (e.g., `"mean"`, `"median"`, `"min"`, `"max"`) — values are `null` if no data.

    Raises
    ------
    ValueError
        If `scale` is missing and `meta["scale_m"]` is not present or invalid.

    Notes
    -----
    - For empty periods (no images), returns a feature with `"n_images": 0` and all statistics as `null`.
    - Geometry is reprojected to the image’s native CRS before reduction for accuracy.
    - Designed for use in time-series generation (e.g., mapping over date sequences).
    """
    
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
    """
    Generate a time series of environmental metrics (e.g., NDVI, LST, precipitation) over a region of interest.

    This function retrieves satellite or gridded data for a specified product, aggregates it over regular 
    time intervals (daily, weekly, monthly, or yearly), computes spatial statistics,and returns results as 
    a pandas DataFrame with standardized columns.

    Parameters
    ----------
    product : str
        Environmental product to retrieve. Supported values include:
        - "NDVI", "EVI" (vegetation indices)
        - "LST" (Land Surface Temperature)
        - "CHIRPS" (precipitation)
    start_date : str
        Start date of the time series in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time series in 'YYYY-MM-DD' format.
    frequency : {"daily", "weekly", "monthly", "yearly"}
        Temporal aggregation interval.
    roi_gdf : geopandas.GeoDataFrame
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries.
        Must be provided; cannot be None.
    satellite : str, optional
        Satellite platform (e.g., "MODIS", "LANDSAT", "SENTINEL2"). Required for vegetation and LST products.
        Ignored for grid-based products like CHIRPS.
    scale : int, optional
        Spatial resolution (in meters) for reduction. If omitted, a product- and sensor-appropriate default 
        is used (e.g., 500 m for MODIS LST, 10 m for Sentinel-2).

    Returns
    -------
    pd.DataFrame
        A DataFrame with one row per time period, containing:
        - `"date"`: Period start as "YYYY-MM-dd"
        - `"product"`: Uppercase product name
        - `"satellite"`: Satellite name (if applicable)
        - Statistic columns (e.g., `"mean"`, `"median"`, `"ndvi"`, `"precipitation_mm"`)
        - `"n_images"`: Number of source images used per period
        - `"unit"`: Measurement unit (e.g., "NDVI", "°C", "mm")
        - (Optional) `"month"`: Full month name (e.g., "January") if `frequency="monthly"`

        Rows with all-null statistics are removed based on product-specific logic.

    Raises
    ------
    ValueError
        If `roi_gdf` is not provided.

    Notes
    -----
    - For MODIS products, the ROI geometry is reprojected to the native sinusoidal projection 
      to ensure accurate spatial reduction.
    - The collection is pre-filtered to the ROI using `filterBounds` for performance.
    - Time periods are generated using calendar-aware intervals (not fixed day counts).
    - Missing or invalid data points are filtered out post-reduction based on the primary metric:
        - LST: removes rows where `"mean"` is null
        - CHIRPS: removes rows where `"precipitation_mm"` is null
        - Vegetation indices: removes rows where the index column (`"ndvi"`, `"evi"`) is null
    - Requires an initialized Earth Engine session (`ee.Initialize()`); ensured via `ee_initialized()`.
    """

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

    start = ee.Date(start_date)
    end = ee.Date(end_date)

    dates = _make_dates(start, end, frequency)

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
    product: str,
    start_date: str,
    end_date: str,
    satellite: Optional[str] = None,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: str = "mean",
) -> ee.Image:
    """
    Generate a single composite Earth Engine image by aggregating a time series of environmental data.

    This function retrieves a filtered ImageCollection for the specified product and time range, 
    applies a temporal reducer (e.g., mean, median), and optionally clips the result to a region of interest.

    Parameters
    ----------
    product : str
        Environmental product name (e.g., "NDVI", "LST", "CHIRPS", "EVI"). Case-insensitive; normalized internally.
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite platform (e.g., "MODIS", "LANDSAT", "SENTINEL2"). Required for sensor-based products; 
        ignored for gridded datasets like CHIRPS.
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame. If provided, the output image is clipped to this geometry.
    reducer : {"mean", "median", "min", "max"}, optional
        Temporal aggregation method applied across the time series (default: "mean").

    Returns
    -------
    ee.Image
        A single-band (or multi-band) composite image with:
        - Band name(s) preserved from the source collection (e.g., "NDVI", "LST_C")
        - Properties including:
            - `"product"`: normalized product name
            - `"satellite"`: satellite used (if applicable)
            - `"start_date"`, `"end_date"`: time range
            - `"reducer"`: aggregation method
            - `"unit"`: measurement unit (e.g., "NDVI", "°C", "mm")

    Notes
    -----
    - Uses internally to handle product-specific compositing logic.
    - For MODIS, the ROI geometry is reprojected to the native projection before clipping (if `roi_gdf` is provided).
    - The input collection is pre-filtered to the ROI using `filterBounds` for efficiency.
    - No cloud masking or quality filtering is applied beyond what is defined in `get_satellite_collection`.
    - Requires an initialized Earth Engine session (`ee.Initialize()`); ensured via `ee_initialized()`.
    """
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


# ------------------------------------
# ONE CollectionImage function
# ------------------------------------

def CollectionImage(
    product: str,
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    satellite: Optional[str] = None,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.ImageCollection:
    """
    Generate an Earth Engine ImageCollection of temporally aggregated composites over regular intervals.

    This function divides the input date range into periods, aggregates imagery 
    within each period using a specified reducer, and returns a time-series ImageCollection suitable 
    for animation, charting, or further analysis.

    Parameters
    ----------
    product : str
        Environmental data product. Supported values include:
        - Vegetation: "NDVI", "EVI"
        - Temperature: "LST"
        - Precipitation: "CHIRPS"
        (Case-insensitive; normalized internally.)
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
    frequency : {"daily", "weekly", "monthly", "yearly"}, optional
        Temporal interval for compositing (default: "monthly").
    satellite : str, optional
        Satellite platform (e.g., "MODIS", "LANDSAT", "SENTINEL2"). Required for sensor-based products; 
        ignored for gridded datasets like CHIRPS.
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame. If provided, the collection is filtered to this region 
        and output images are clipped to it.
    reducer : {"mean", "median", "min", "max", "sum"}, optional
        Temporal aggregation method. For "CHIRPS", "sum" is allowed (for total precipitation); 
        other products support only statistical reducers (default: "mean").

    Returns
    -------
    ee.ImageCollection
        An ImageCollection where each image:
        - Represents one time period (e.g., January 2023)
        - Contains band(s) named per the source product
        - Has properties:
            - `"system:time_start"`: period start (milliseconds since Unix epoch)
            - `"period_start"`: formatted as "YYYY-MM-dd"
            - `"product"`, `"satellite"`, `"frequency"`, `"reducer"`, `"unit"`
        - (For monthly frequency) Includes a `"month"` property with full month name (e.g., "January")

    Raises
    ------
    ValueError
        If an unsupported reducer is specified for the given product (e.g., "sum" for NDVI).

    Notes
    -----
    - For MODIS vegetation products, the ROI geometry is reprojected to the native sinusoidal projection 
      before filtering and clipping to ensure spatial accuracy.
    - The collection is pre-filtered to the ROI (if provided) for performance.
    - Time periods are generated using calendar-aware intervals (not fixed day counts).
    - CHIRPS supports `"sum"` to compute total precipitation over the period; all other products use 
      pixel-wise statistics (mean, median, etc.).
    - Requires an initialized Earth Engine session (`ee.Initialize()`); ensured via `ee_initialized()`.
    """

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







