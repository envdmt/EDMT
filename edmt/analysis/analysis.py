import ee
from typing import Optional, Literal
import geopandas as gpd
import shapely


def ensure_ee_initialized():
    """
    Initialize Google Earth Engine if not already initialized.
    """
    if not ee.data._initialized:
        ee.Initialize()


def gdf_to_ee_geometry(
    gdf: gpd.GeoDataFrame
) -> ee.Geometry:
    """
    Convert a GeoDataFrame containing Polygon or MultiPolygon geometries to an Earth Engine Geometry.

    The input GeoDataFrame is reprojected to WGS84 (EPSG:4326) if necessary, and all geometries 
    are dissolved into a single geometry using unary union before conversion.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        A GeoDataFrame containing one or more Polygon or MultiPolygon features. 
        Must have a valid coordinate reference system (CRS).

    Returns
    -------
    ee.Geometry
        An Earth Engine Geometry object representing the union of all input geometries, 
        in WGS84 (longitude/latitude).

    Raises
    ------
    ValueError
        If the GeoDataFrame is empty or lacks a CRS.
    """
    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")

    if gdf.crs is None:
        raise ValueError("GeoDataFrame must have a CRS")

    # Ensure WGS84 for Earth Engine
    gdf = gdf.to_crs(epsg=4326)

    geom = gdf.union_all()
    geojson = shapely.geometry.mapping(geom)
    return ee.Geometry(geojson)


def to_celsius(
    img: ee.Image,factors: dict
) -> ee.Image:
    """
    Convert a raw land surface temperature (LST) image from digital numbers to degrees Celsius.

    The conversion applies satellite-specific scaling factors to transform raw pixel values 
    to Kelvin, then subtracts 273.15 to obtain Celsius.

    Parameters
    ----------
    img : ee.Image
        An Earth Engine image containing raw LST band values (e.g., "LST_Day_1km", "ST_B10").
    factors : dict
        A dictionary containing scaling parameters with keys:
        - "multiply" (float): Multiplicative scaling factor.
        - "add" (float): Additive offset.
        These are applied as: scaled_value = img * multiply + add.

    Returns
    -------
    ee.Image
        An image with LST values in degrees Celsius, preserving the original band name 
        and copying essential metadata (e.g., 'system:time_start').
    """
    return img.multiply(factors["multiply"]).add(factors["add"]).subtract(273.15).copyProperties(
        img, ["system:time_start"]
    )


def compute_period(
    frequency: str, 
    start: ee.Date,
    collection: ee.ImageCollection, 
    geometry: ee.Geometry, 
    scale: Optional[int] = None
) -> ee.Number:
    """
    Compute the spatial mean of a single-band image over a specified time period and region.

    Aggregates images in the collection over a temporal window (weekly, monthly, or yearly), 
    computes the mean image, then reduces it to a single scalar value over the given geometry.

    Parameters
    ----------
    frequency : {"weekly", "monthly", "yearly"}
        Temporal aggregation interval that defines the period length.
    start : ee.Date
        Start date of the period.
    collection : ee.ImageCollection
        A single-band ImageCollection (e.g., LST, NDVI) to aggregate and reduce.
    geometry : ee.Geometry
        Region of interest for spatial averaging.
    scale : int, optional
        Spatial resolution (in meters) at which to perform the reduction. If omitted, 
        Earth Engine will use the native resolution of the input data.

    Returns
    -------
    ee.Number
        The mean pixel value over the geometry during the period. Returns `null` (as an ee.Number) 
        if no valid pixels are available.

    Raises
    ------
    ValueError
        If `frequency` is not one of "weekly", "monthly", or "yearly".

    Notes
    -----
    - Uses `ee.Reducer.mean()` with `maxPixels=1e13` to accommodate large geometries.
    - The input collection must contain only one band; behavior is undefined otherwise.
    - This function returns an Earth Engine object (`ee.Number`), not a Python float—use `.getInfo()` 
      to retrieve the value client-side.
    """

    start = ee.Date(start)
    if frequency == "weekly":
        end = start.advance(1, "week")
    elif frequency == "monthly":
        end = start.advance(1, "month")
    elif frequency == "yearly":
        end = start.advance(1, "year")
    else:
        raise ValueError(f"Invalid frequency: {frequency}")

    img = collection.filterDate(start, end).mean()
    proj = img.projection()
    geom_in_img_crs = geometry.transform(proj, 1)

    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.median(), sharedInputs=True)
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True)
    )

    stats = img.reduceRegion(
        reducer=reducer,
        geometry=geom_in_img_crs,
        scale=scale,
        maxPixels=1e13,
    )

    val = ee.Algorithms.If(
        stats.size().gt(0),
        stats.values().get(0),
        None
    )

    return ee.Dictionary(stats)


def Reducer(
    collection: ee.ImageCollection,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:
    """
    Apply a temporal reducer to an ImageCollection to produce a single composite image.

    This utility function simplifies common reduction operations over time by mapping string 
    identifiers to Earth Engine’s built-in collection reducers.

    Parameters
    ----------
    collection : ee.ImageCollection
        Input image collection to reduce. Must contain at least one image.
    reducer : {"mean", "median", "min", "max"}, optional
        Type of reducer to apply across the collection (default: "mean").

    Returns
    -------
    ee.Image
        A single composite image resulting from the specified reduction operation. 
        Band names and data types are preserved from the input collection.

    Raises
    ------
    ValueError
        If `reducer` is not one of the supported options.

    Notes
    -----
    - This function does not modify band values or metadata beyond the reduction operation.
    - No spatial clipping or masking is applied—only temporal aggregation.
    """

    r = reducer.lower()
    if r == "mean":
        return collection.mean()
    if r == "median":
        return collection.median()
    if r == "min":
        return collection.min()
    if r == "max":
        return collection.max()
    raise ValueError("reducer must be one of: mean, median, min, max")


def _mask_s2_sr_clouds(
    img: ee.Image
) -> ee.Image:
    """
    Apply a cloud and cirrus mask to a Sentinel-2 Surface Reflectance (SR) image using the QA60 band.

    This function masks out pixels flagged as cloudy or cirrus-contaminated based on bits 10 and 11 
    of the `QA60` quality assessment band.

    - Bit 10 corresponds to opaque clouds; bit 11 corresponds to cirrus.
    - This mask does not account for snow, water, or other QA flags—only cloud/cirrus.
    - The function assumes the input image contains the "QA60" band.

    Parameters
    ----------
    img : ee.Image
        A Sentinel-2 SR image from the "COPERNICUS/S2_SR" collection, containing the "QA60" band.

    Returns
    -------
    ee.Image
        The input image with cloud and cirrus pixels masked out (set to no-data).
    """

    qa = img.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
    return img.updateMask(mask)


def _mask_landsat_c2_l2_clouds(
    img: ee.Image
) -> ee.Image:
    """
    Apply a comprehensive cloud, shadow, and cirrus mask to a Landsat Collection 2 Level 2 image 
    using the QA_PIXEL band.

    Masks pixels flagged as fill, dilated cloud, cirrus, cloud, or cloud shadow based on bits 0–4 
    of the `QA_PIXEL` band.

    QA_PIXEL bit interpretation (per USGS):
      - Bit 0: Fill (no data)
      - Bit 1: Dilated cloud
      - Bit 2: Cirrus (high confidence)
      - Bit 3: Cloud
      - Bit 4: Cloud shadow
    - All five conditions must be clear (bit = 0) for a pixel to be retained.

    Parameters
    ----------
    img : ee.Image
        A Landsat C2 L2 image from collections such as "LANDSAT/LC08/C02/T1_L2", containing the "QA_PIXEL" band.

    Returns
    -------
    ee.Image
        The input image with invalid or obscured pixels (cloud, shadow, cirrus, etc.) masked out.
    """

    qa = img.select("QA_PIXEL")
    mask = (
        qa.bitwiseAnd(1 << 0).eq(0)
        .And(qa.bitwiseAnd(1 << 1).eq(0))
        .And(qa.bitwiseAnd(1 << 2).eq(0))
        .And(qa.bitwiseAnd(1 << 3).eq(0))
        .And(qa.bitwiseAnd(1 << 4).eq(0))
    )
    return img.updateMask(mask)


def _ndvi_from_nir_red(img: ee.Image, nir: str, red: str) -> ee.Image:
    """
    Compute the Normalized Difference Vegetation Index (NDVI) from user-specified NIR and Red bands.

    NDVI is calculated as (NIR − Red) / (NIR + Red) using Earth Engine’s built-in `normalizedDifference` 
    method, which handles division by zero gracefully (returning masked pixels where denominator is zero).

    Parameters
    ----------
    img : ee.Image
        Input image containing the required spectral bands.
    nir : str
        Name of the near-infrared band in the input image (e.g., "B8" for Sentinel-2, "SR_B5" for Landsat).
    red : str
        Name of the red band in the input image (e.g., "B4" for Sentinel-2, "SR_B4" for Landsat).

    Returns
    -------
    ee.Image
        A single-band image with band name "NDVI" and values in the theoretical range [-1, 1]. 
        The output preserves the "system:time_start" property from the input image to maintain 
        temporal metadata for time-series operations.

    Notes
    -----
    - This is a low-level helper intended for use within sensor-specific NDVI processing pipelines.
    - Input bands should be in comparable units (e.g., surface reflectance); no scaling is applied internally.
    - Pixels with zero or negative denominators (e.g., water, shadows) are automatically masked by 
      `normalizedDifference`.
    """
    ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
    return ndvi.copyProperties(img, ["system:time_start"])


def compute_per_period(
    date: ee.Date,
    frequency: str,
    collection: ee.ImageCollection,
    satellite: str,
    roi: Optional[ee.Geometry] = None,
    name: str = "composite",
) -> ee.Image:
    """
    Compute a single composite image over a time period (weekly, monthly, or yearly) from an ImageCollection.

    This helper function aggregates images within a specified temporal window using the mean reducer, 
    renames the output band, attaches metadata, and optionally clips to a region of interest.

    Parameters
    ----------
    date : ee.Date
        Start date of the aggregation period.
    frequency : {"weekly", "monthly", "yearly"}
        Temporal interval defining the period length. Determines the end date via Earth Engine’s 
        calendar-aware `advance()` method.
    collection : ee.ImageCollection
        Input image collection to aggregate. Assumed to be pre-filtered in time and space as needed.
    satellite : str
        Name of the source satellite (e.g., "MODIS", "LANDSAT"). Used only for metadata labeling.
    roi : ee.Geometry, optional
        Region of interest for clipping the output image. If provided, the result is spatially bounded.
    name : str, optional
        Name to assign to the output band (default: "composite").

    Returns
    -------
    ee.Image
        A single-band composite image with:
        - Band renamed to `name`
        - Properties: 
            - `"system:time_start"`: period start time in milliseconds since Unix epoch
            - `"period_start"`: formatted as "YYYY-MM-dd"
            - `"satellite"`: uppercase satellite name
    """

    d = ee.Date(date)
    if frequency == "weekly":
        end = d.advance(1, "week")
    elif frequency == "monthly":
        end = d.advance(1, "month")
    else:
        end = d.advance(1, "year")

    img = collection.filterDate(d, end).mean().rename(name)
    img = img.set("system:time_start", d.millis())
    img = img.set("period_start", d.format("YYYY-MM-dd"))
    img = img.set("satellite", satellite.upper())

    if roi is not None:
        img = img.clip(roi)

    return img