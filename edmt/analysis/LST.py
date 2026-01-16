import pandas as pd
from typing import Optional
import geopandas as gpd
import shapely
import ee

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


def get_satellite_collection(
    satellite: str, start_date: str, end_date: str
) -> tuple[ee.ImageCollection, dict]:
    """
    Retrieve an Earth Engine ImageCollection and associated scaling parameters 
    for land surface temperature (LST) from a specified satellite.

    Parameters
    ----------
    satellite : str
        Name of the satellite sensor. Supported options: "MODIS", "LANDSAT", "GCOM", or "ECOSTRESS".
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

    elif satellite == "ECOSTRESS":
        collection = (
            ee.ImageCollection("NASA/ECOSTRESS/L2T_LSTE/V2")
            .select("LST")
            .filterDate(start_date, end_date)
        )
        factors = {"multiply": 1.0, "add": 0.0, "band": "LST"}

    else:
        raise ValueError(f"Unsupported satellite: {satellite}")

    return collection, factors


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
        Name of the satellite ("MODIS", "LANDSAT", "GCOM", "ECOSTRESS") to select default scale.
    scale : int, optional
        Spatial resolution (meters). If None, a default per satellite is used:
            MODIS: 1000
            LANDSAT: 30
            GCOM: 4638.3
            ECOSTRESS: 70

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
            "GCOM": 4638.3,
            "ECOSTRESS": 70
        }
        if satellite not in default_scales:
            raise ValueError(f"Unknown satellite for default scale: {satellite}")
        scale = default_scales[satellite]

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

    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
    )

    lst_mean_val = ee.Algorithms.If(
        stats.size().gt(0),
        stats.values().get(0),
        None
    )

    return ee.Feature(
        None,
        {
            "date": start.format("YYYY-MM-dd"),
            "lst_mean": lst_mean_val,
        },
    )


def compute_lst_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: int = 1000,
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

    geometry = gdf_to_ee_geometry(roi_gdf)

    # Get collection + conversion factors
    collection, factors = get_satellite_collection(satellite, start_date, end_date)
    collection = collection.map(lambda img: to_celsius(img, factors))

    # Generate time steps
    step_days = {"weekly": 7, "monthly": 30, "yearly": 365}[frequency.lower()]

    dates = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        step_days * 24 * 60 * 60 * 1000,
    )

    # Compute LST per period
    features = ee.FeatureCollection(
        dates.map(lambda d: compute_period_feature(ee.Date(d), collection, geometry, scale, frequency))
    )

    # Convert to pandas DataFrame
    features_info = features.getInfo()["features"]
    rows = [
        {
            "date": f["properties"]["date"],
            "lst_mean": f["properties"].get("lst_mean"),
            "satellite": satellite.upper(),
            "unit": "°C",
        }
        for f in features_info
        if f["properties"].get("lst_mean") is not None
    ]

    return pd.DataFrame(rows)


