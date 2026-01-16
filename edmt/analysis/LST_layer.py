import ee
from typing import Optional, Literal
from .LST import (
    ensure_ee_initialized,
    get_satellite_collection,
    to_celsius
)

import ee
from typing import Optional, Literal
from edmt.analysis import (
    ensure_ee_initialized,
    get_satellite_collection,
    to_celsius
)

def get_lst_image(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    roi: Optional[ee.Geometry] = None,
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
    roi : ee.Geometry, optional
        Region of interest to clip the output image. If None, the full global extent is returned.
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
    ensure_ee_initialized()

    collection, factors = get_satellite_collection(satellite, start_date, end_date)
    collection_c = collection.map(lambda img: to_celsius(img, factors))

    reducer = reducer.lower()
    if reducer == "mean":
        img = collection_c.mean()
    elif reducer == "median":
        img = collection_c.median()
    elif reducer == "min":
        img = collection_c.min()
    elif reducer == "max":
        img = collection_c.max()
    else:
        raise ValueError("reducer must be one of: mean, median, min, max")

    img = img.rename("LST_C")

    if roi is not None:
        img = img.clip(roi)

    return img


def get_lst_period_collection(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: Literal["weekly", "monthly", "yearly"] = "monthly",
    roi: Optional[ee.Geometry] = None,
    scale: Optional[int] = None,
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
    roi : ee.Geometry, optional
        Region of interest to clip each composite image. If None, images retain their full extent.
    scale : int, optional
        *Reserved for future use.* Currently not applied in processing.

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

    ensure_ee_initialized()

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

    def per_period(d):
        d = ee.Date(d)
        if freq == "weekly":
            end = d.advance(1, "week")
        elif freq == "monthly":
            end = d.advance(1, "month")
        else:
            end = d.advance(1, "year")

        img = collection_c.filterDate(d, end).mean().rename("LST_C")
        img = img.set("system:time_start", d.millis())
        img = img.set("period_start", d.format("YYYY-MM-dd"))
        img = img.set("satellite", satellite.upper())

        if roi is not None:
            img = img.clip(roi)

        return img

    return ee.ImageCollection(dates.map(per_period))


