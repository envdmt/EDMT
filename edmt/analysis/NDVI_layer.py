import ee
import geopandas as gpd
from typing import Optional, Literal
from edmt.analysis import (
    ee_initialized,
    gdf_to_ee_geometry,
    Reducer,
    compute_per_period
)

from .NDVI import (
    get_ndvi_collection
)


def get_ndvi_image(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:
    """
    Generate a single composite NDVI image from satellite data over a specified time period, 
    suitable for visualization or mapping.

    The function retrieves preprocessed NDVI data from a chosen satellite product, applies 
    a temporal reducer (e.g., mean, median), and optionally clips the result to a region of interest.

    Parameters
    ----------
    start_date : str
        Start date of the compositing period in 'YYYY-MM-DD' format.
    end_date : str
        End date of the compositing period in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite or product name. Supported options:
        - "LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY": 8-day Landsat NDVI composites
        - "MODIS": MOD13Q1 (16-day, 250m)
        - "SENTINEL", "SENTINEL2", "S2": Sentinel-2 Harmonized
        - "VIIRS", "NOAA_VIIRS", "NOAA": NOAA CDR VIIRS NDVI
        (default: "MODIS").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        If provided, the output image is clipped to this region.
    reducer : {"mean", "median", "min", "max"}, optional
        Temporal aggregation method to combine NDVI images across the time window (default: "mean").

    Returns
    -------
    ee.Image
        A single-band Earth Engine image with band name "NDVI" and values in the range [-1, 1].
        
    """
    ee_initialized()

    roi: Optional[ee.Geometry] = None
    if roi_gdf is not None:
        roi = gdf_to_ee_geometry(roi_gdf)

    collection, _ = get_ndvi_collection(satellite, start_date, end_date)

    img = Reducer(collection, reducer=reducer).rename("NDVI")

    if roi is not None:
        img = img.clip(roi)

    return img


def get_ndvi_image_collection(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: Literal["weekly", "monthly", "yearly"] = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
) -> ee.ImageCollection:
    """
    Generate an Earth Engine ImageCollection of NDVI composites aggregated over regular time periods 
    (weekly, monthly, or yearly).

    Each image in the collection represents the mean NDVI over one period, includes metadata about 
    the period start, and is optionally clipped to a region of interest.

    Parameters
    ----------
    start_date : str
        Start date of the overall time window in 'YYYY-MM-DD' format.
    end_date : str
        End date of the overall time window in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite or product name. Supported options:
        - "LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY": 8-day Landsat NDVI composites
        - "MODIS": MOD13Q1 (16-day, 250m)
        - "SENTINEL", "SENTINEL2", "S2": Sentinel-2 Harmonized
        - "VIIRS", "NOAA_VIIRS", "NOAA": NOAA CDR VIIRS NDVI
        (default: "MODIS").
    frequency : {"weekly", "monthly", "yearly"}, optional
        Temporal aggregation interval for compositing (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        If provided, output images are clipped to this region.

    Returns
    -------
    ee.ImageCollection
        An ImageCollection where each image:
        - Contains one band named `"NDVI"` with values in the range [-1, 1].
        - Has the property `"system:time_start"` set to the period start (in milliseconds since Unix epoch).
        - Includes additional properties: `"period_start"` (formatted as "YYYY-MM-dd") and `"satellite"`.

    Raises
    ------
    ValueError
        If `frequency` is not one of the supported options.

    """

    ee_initialized()


    roi: Optional[ee.Geometry] = None
    if roi_gdf is not None:
        roi = gdf_to_ee_geometry(roi_gdf)

    collection, _ = get_ndvi_collection(satellite, start_date, end_date)

    freq = frequency.lower()
    if freq not in {"weekly", "monthly", "yearly"}:
        raise ValueError("frequency must be one of: weekly, monthly, yearly")

    step_days = {"weekly": 7, "monthly": 30, "yearly": 365}[freq]
    dates = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        step_days * 24 * 60 * 60 * 1000,
    )

    img_coll = ee.ImageCollection(
        dates.map(
            lambda d: compute_per_period(
                ee.Date(d),
                frequency,
                collection,
                satellite,
                roi=roi
            )
        )
    )

    if freq == "monthly":
            img_coll = img_coll.map(
                lambda img: img.set(
                    {
                        "month": ee.Date(img.get("system:time_start")).format("MMMM"),
                    }
                )
            )

    return img_coll.sort("system:time_start")


