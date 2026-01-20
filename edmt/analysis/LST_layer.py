import ee
import geopandas as gpd
from typing import Optional, Literal
from edmt.analysis import (
    ee_initialized,
    gdf_to_ee_geometry,
    to_celsius,
    Reducer,
    compute_per_period,
)
from .LST import (
    get_lst_collection,
)


def get_lst_image(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:
    """
    Generate a single composite Earth Engine image of Land Surface Temperature (LST) in degrees Celsius 
    for visualization or mapping purposes.

    The function retrieves LST data from a specified satellite sensor over a given date range, 
    converts raw values to Celsius, applies a temporal reducer (e.g., mean, median), and optionally 
    clips the result to a region of interest.

    Parameters
    ----------
    start_date : str
        Start date of the time window in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time window in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame (Polygon/MultiPolygon). If provided, will be
        converted internally using gdf_to_ee_geometry() and used for filterBounds + clip.
    reducer : {"mean", "median", "min", "max"}, optional
        Temporal aggregation method to combine images across the time period (default: "mean").

    Returns
    -------
    ee.Image
        A single-band Earth Engine image with band name "LST_C", containing LST values in °C. 
        Suitable for display with `Map.addLayer(...)` in Earth Engine environments.

    Raises
    ------
    ValueError
        If an unsupported reducer is provided.

    """
    ee_initialized()

    roi: Optional[ee.Geometry] = None
    if roi_gdf is not None:
        roi = gdf_to_ee_geometry(roi_gdf)

    collection, factors = get_lst_collection(satellite, start_date, end_date)
    
    if roi is not None:
        collection = collection.filterBounds(roi)

    collection_c = collection.map(lambda img: to_celsius(img, factors))

    img = Reducer(collection_c, reducer=reducer).rename("LST_C")

    if roi is not None:
        img = img.clip(roi)

    return img


def get_lst_image_collection(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: Literal["weekly", "monthly", "yearly"] = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
) -> ee.ImageCollection:
    """
    Generate an Earth Engine ImageCollection of Land Surface Temperature (LST) composites 
    aggregated over regular time periods (weekly, monthly, or yearly), in degrees Celsius.

    Each image in the collection represents the mean LST over one period, includes metadata 
    about the period start, and is optionally clipped to a region of interest.

    Parameters
    ----------
    start_date : str
        Start date of the overall time window in 'YYYY-MM-DD' format.
    end_date : str
        End date of the overall time window in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
    frequency : {"weekly", "monthly", "yearly"}, optional
        Temporal aggregation interval for compositing (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame (Polygon/MultiPolygon). If provided, will be
        converted internally using gdf_to_ee_geometry() and used for filterBounds + clip.
    

    Returns
    -------
    ee.ImageCollection
        An ImageCollection where each image:
        - Contains one band named `"LST_C"` with LST values in °C.
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

    collection, factors = get_satellite_collection(satellite, start_date, end_date)
    collection_c = collection.map(lambda img: to_celsius(img, factors))

    freq = frequency.lower()
    if freq not in {"weekly", "monthly", "yearly"}:
        raise ValueError("frequency must be one of: weekly, monthly, yearly")

    step_days = {"weekly": 7, "monthly": 30, "yearly": 365}[freq]
    dates = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        step_days * 24 * 60 * 60 * 1000,
    )

    return ee.ImageCollection(
        dates.map(
            lambda d: compute_per_period(
                ee.Date(d),
                frequency,
                collection_c,
                satellite,
                roi=roi
            )
        )
    )




