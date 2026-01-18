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
    scale: Optional[int] = None
) -> ee.Feature:
    """
    Compute spatial summary statistics (mean, median, min, max) of a single-band image over a time period 
    and return them as an Earth Engine Feature with metadata.

    This function aggregates imagery over a temporal window (weekly, monthly, or yearly), computes multiple 
    spatial statistics over a region of interest, and packages the results into a feature suitable for 
    time series export or charting.

    Parameters
    ----------
    start : ee.Date
        Start date of the aggregation period.
    collection : ee.ImageCollection
        A single-band ImageCollection (e.g., LST in Kelvin or Celsius) to process.
    geometry : ee.Geometry
        Region of interest over which to compute spatial statistics.
    frequency : {"weekly", "monthly", "yearly"}
        Temporal interval defining the period length.
    satellite : str
        Satellite name used to infer default spatial resolution if `scale` is not provided. 
        Supported: "MODIS", "LANDSAT", "GCOM".
    scale : int, optional
        Spatial resolution (in meters) for the reduction. If omitted, a sensor-specific default is used:
        - MODIS: 1000 m
        - Landsat: 30 m
        - GCOM: ~4638 m

    Returns
    -------
    ee.Feature
        A feature with no geometry and properties including:
        - "date": Period start formatted as "YYYY-MM-dd"
        - "satellite": Uppercase satellite name
        - "{band}_mean", "{band}_median", "{band}_min", "{band}_max": Computed statistics  
          (e.g., "LST_Day_1km_mean" → "LST_Day_1km_mean"; band name preserved from input)

    Raises
    ------
    ValueError
        If `frequency` is invalid or if `satellite` is unknown and `scale` is not provided.
    
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
    
    keys = ee.List(stats.keys())

    def _make_prop(k):
        k = ee.String(k)
        out_name = (
            k.replace("_mean", "_mean")
             .replace("_median", "_median")
             .replace("_min", "_min")
             .replace("_max", "_max")
        )
        return ee.Dictionary().set(out_name, stats.get(k))

    props = ee.Dictionary(keys.iterate(lambda k, acc: ee.Dictionary(acc).combine(_make_prop(k), True), ee.Dictionary()))

    props = props.set("date", ee.Date(start).format("YYYY-MM-dd"))
    props = props.set("satellite", satellite.upper())

    return ee.Feature(None, props)




def compute_lst_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    """
    Compute a time series of Land Surface Temperature (LST) statistics over a region of interest 
    using Google Earth Engine.

    This function retrieves LST data from a specified satellite, converts it to degrees Celsius, 
    aggregates it over regular time intervals (weekly, monthly, or yearly), and computes multiple 
    spatial statistics (mean, median, min, max) for each period.

    Parameters
    ----------
    start_date : str
        Start date of the time series in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time series in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite data source. Supported options: "MODIS", "LANDSAT", or "GCOM" (default: "MODIS").
    frequency : {"weekly", "monthly", "yearly"}, optional
        Temporal aggregation interval (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        Must be provided; otherwise, a ValueError is raised.
    scale : int, optional
        Spatial resolution (in meters) for reduction. If omitted, a sensor-specific default is used:
        - MODIS: 1000 m
        - Landsat: 30 m
        - GCOM: ~4638 m

    Returns
    -------
    pd.DataFrame
        A DataFrame where each row corresponds to one time period, with columns including:
        - "date": Period start as "YYYY-MM-dd"
        - "satellite": Uppercase satellite name
        - "{band}_mean", "{band}_median", "{band}_min", "{band}_max": LST statistics in °C  
          (e.g., "LST_Day_1km_mean")
        - "unit": Always "°C"
        Periods with no valid data (all stats null) are excluded.

    Raises
    ------
    ValueError
        If `roi_gdf` is not provided or if `frequency` is invalid.

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

    rows = []
    for f in features_info:
        p = f["properties"]
        if any(v is not None for k, v in p.items() if k.endswith("_mean")):
            p["unit"] = factors.get("unit", "°C")
            rows.append(p)

    return pd.DataFrame(rows)




