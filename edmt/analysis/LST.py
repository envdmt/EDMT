import ee
import pandas as pd
from typing import Optional
import geopandas as gpd
from edmt.analysis import (
    to_celsius,
    gdf_to_ee_geometry,
    compute_period,
    ensure_ee_initialized
)


def get_satellite_collection(
    satellite: str, start_date: str, end_date: str
) -> tuple[ee.ImageCollection, dict]:
    """
    Retrieve an Earth Engine ImageCollection and associated scaling parameters 
    for land surface temperature (LST) from a specified satellite.

    Parameters
    ----------
    satellite : str
        Name of the satellite sensor. Supported options: "MODIS", "LANDSAT", "GCOM".
    start_date : str
        Start date for filtering the collection in 'YYYY-MM-DD' format.
    end_date : str
        End date for filtering the collection in 'YYYY-MM-DD' format.

    Returns
    -------
    tuple[ee.ImageCollection, dict]
        A tuple containing:
        - An ee.ImageCollection filtered to the specified date range and pre-selected band.
        - A dictionary with scaling factors (`multiply`, `add`) and the selected band name,
          used to convert raw digital numbers to physical LST values (in Kelvin).

    Raises
    ------
    ValueError
        If the provided satellite name is not supported.
    """
    satellite = satellite.upper()

    if satellite == "MODIS":
        collection = (
            ee.ImageCollection("MODIS/061/MOD11A1")
            .select("LST_Day_1km")
            .filterDate(start_date, end_date)
        )
        factors = {"multiply": 0.02, "add": 0.0, "band": "LST_Day_1km"}

    elif satellite == "LANDSAT":
        collection = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .select("ST_B10")
            .filterDate(start_date, end_date)
        )
        factors = {"multiply": 0.00341802, "add": 149.0, "band": "ST_B10"}

    elif satellite == "GCOM":
        collection = (
            ee.ImageCollection("JAXA/GCOM-C/L3/LAND/LST/V3")
            .select("LST_AVE")
            .filterDate(start_date, end_date)
        )
        factors = {"multiply": 0.02, "add": 0.0, "band": "LST_AVE"}

    else:
        raise ValueError(f"Unsupported satellite: {satellite}")

    return collection, factors


def compute_period_feature(
    start: ee.Date, 
    collection: ee.ImageCollection, 
    geometry: ee.Geometry, 
    frequency: str,
    satellite: str,
    scale: int = None
) -> ee.Feature:
    """
    Compute the mean land surface temperature (LST) over a specified time period 
    (weekly, monthly, or yearly) for a given region, using a default scale per satellite
    if not provided.

    Parameters
    ----------
    start : ee.Date
        The start date of the aggregation period.
    collection : ee.ImageCollection
        An ImageCollection containing LST images (assumed to be in Kelvin or already scaled).
    geometry : ee.Geometry
        The region of interest over which to compute the spatial mean.
    frequency : str
        Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly".
    satellite : str
        Name of the satellite ("MODIS", "LANDSAT", "GCOM") to select default scale.
    scale : int, optional
        Spatial resolution (meters). If None, a default per satellite is used:
            MODIS: 1000
            LANDSAT: 30
            GCOM: 4638.3

    Returns
    -------
    ee.Feature
        A feature with no geometry and properties:
        - "date": Start date of the period as "YYYY-MM-dd".
        - "lst_mean": Mean LST value over the geometry. Null if no valid pixels.
    """
    if scale is None:
        satellite = satellite.upper()
        default_scales = {
            "MODIS": 1000,
            "LANDSAT": 30,
            "GCOM": 4638.3
        }
        if satellite not in default_scales:
            raise ValueError(f"Unknown satellite for default scale: {satellite}")
        scale = default_scales[satellite]

    stats = compute_period(
        frequency=frequency,
        start=start,
        collection=collection,
        geometry=geometry,
        scale=scale,
    )

    return ee.Feature(
        None,
        {
            "date": start.format("YYYY-MM-dd"),
            "lst_mean": stats.get("LST_mean"),
            "lst_median": stats.get("LST_median"),
            "lst_min": stats.get("LST_min"),
            "lst_max": stats.get("LST_max"),
        },
    )


def compute_lst_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    """
    Compute a time series of mean Land Surface Temperature (LST) over a region of interest 
    using Google Earth Engine (GEE) satellite data.

    The function retrieves LST data from a specified satellite sensor, converts it to degrees 
    Celsius, aggregates it over regular time intervals (weekly, monthly, or yearly), and returns 
    the results as a pandas DataFrame.

    Parameters
    ----------
    start_date : str
        Start date of the time series in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time series in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
    frequency : str, optional
        Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly" 
        (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing a single Polygon or MultiPolygon geometry. 
        Must be provided; otherwise, a ValueError is raised.
    scale : int, optional
        Spatial resolution (in meters) for the reduction operation (default: 1000).

    Returns
    -------
    pd.DataFrame
        A DataFrame with columns:
        - "date": Start date of each period as "YYYY-MM-dd".
        - "lst_mean": Mean LST in degrees Celsius for that period.
        - "satellite": Name of the satellite used.
        - "unit": Always "°C".
        Rows with no valid LST data (e.g., due to cloud cover or missing imagery) are excluded.

    Raises
    ------
    ValueError
        If `roi_gdf` is not provided.

    """
    if roi_gdf is None:
        raise ValueError("Provide roi_gdf (Region of Interest)")

    ensure_ee_initialized()

    geometry = gdf_to_ee_geometry(roi_gdf)

    collection, factors = get_satellite_collection(satellite, start_date, end_date)
    collection = collection.map(lambda img: to_celsius(img, factors))

    freq = frequency.lower()
    step_days = {"weekly": 7, "monthly": 30, "yearly": 365}.get(freq)
    if step_days is None:
        raise ValueError("frequency must be one of: weekly, monthly, yearly")

    dates = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        step_days * 24 * 60 * 60 * 1000,
    )

    features = ee.FeatureCollection(
        dates.map(lambda d: compute_period_feature(
            ee.Date(d),
            collection,
            geometry,
            freq,
            satellite,
            scale=scale
        ))
    )

    features_info = features.getInfo()["features"]

    return pd.DataFrame([
        {
            "date": f["properties"]["date"],
            "lst_mean": f["properties"].get("lst_mean"),
            "lst_median": f["properties"].get("lst_median"),
            "lst_min": f["properties"].get("lst_min"),
            "lst_max": f["properties"].get("lst_max"),
            "unit": factors["unit"],
        }
        for f in features_info
        if f["properties"].get("lst_mean") is not None
    ])




