import ee 
import geopandas as gpd
import pandas as pd
from typing import Optional, Tuple
from edmt.analysis import (
    ensure_ee_initialized,
    compute_period,
    gdf_to_ee_geometry,
    _ndvi_from_nir_red
)




def get_ndvi_collection(
    satellite: str,
    start_date: str,
    end_date: str,
) -> Tuple[ee.ImageCollection, dict]:
    """
    Retrieve a preprocessed Earth Engine ImageCollection containing NDVI (Normalized Difference 
    Vegetation Index) values, along with metadata parameters.

    The output collection contains a single band named "NDVI" with float values in the range [-1, 1]. 
    Raw reflectance data is scaled appropriately per sensor, and cloud masking is applied where supported.

    - **MODIS**: NDVI is scaled by 0.0001 (as per product specification).
    - **Landsat 8/9**: Surface reflectance bands are scaled using:  
      `reflectance = DN * 0.0000275 - 0.2`. Cloud, shadow, cirrus, and fill pixels are masked using QA_PIXEL.
    - **Sentinel-2**: Reflectance values are divided by 10,000. Images with >60% cloud cover are excluded, 
      and additional pixel-level cloud/cirrus masking is applied via QA60.

    Parameters
    ----------
    satellite : str
        Satellite platform. Supported options:
        - "MODIS": Uses MOD13Q1 (16-day L3 global 250m)
        - "LANDSAT": Merges Landsat 8 & 9 Collection 2 Level 2 SR
        - "SENTINEL", "SENTINEL2", or "S2": Uses Sentinel-2 SR Harmonized (COPERNICUS/S2_SR_HARMONIZED)
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.

    Returns
    -------
    tuple[ee.ImageCollection, dict]
        - **ImageCollection**: Temporally filtered collection of NDVI images, each with a "NDVI" band 
          and preserved "system:time_start" property.
        - **params**: Dictionary with keys:
            - "band": Name of the NDVI band ("NDVI")
            - "unit": Unit identifier ("NDVI")

    Raises
    ------
    ValueError
        If the provided satellite name is not supported.

    """
    sat = satellite.upper()

    if sat == "MODIS":
        ic = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select("NDVI")
            .map(lambda img: img.multiply(0.0001).rename("NDVI").copyProperties(img, ["system:time_start"]))
        )
        params = {"band": "NDVI", "unit": "NDVI"}
        return ic, params

    if sat == "LANDSAT":
        ic8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2").filterDate(start_date, end_date)
        ic9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterDate(start_date, end_date)
        ic = ic8.merge(ic9)

        def _to_ndvi(img: ee.Image) -> ee.Image:
            img = _mask_landsat_c2_l2_clouds(img)

            red = img.select("SR_B4").multiply(0.0000275).add(-0.2)
            nir = img.select("SR_B5").multiply(0.0000275).add(-0.2)

            return _ndvi_from_nir_red(img, nir, red)

        ic = ic.map(_to_ndvi)
        params = {"band": "NDVI", "unit": "NDVI"}
        return ic, params

    if sat in ("SENTINEL", "SENTINEL2", "S2"):
        ic = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 60))
        )

        def _to_ndvi(img: ee.Image) -> ee.Image:
            img = _mask_s2_sr_clouds(img)

            red = img.select("B4").divide(10000.0)
            nir = img.select("B8").divide(10000.0)

            return _ndvi_from_nir_red(img, nir, red)

        ic = ic.map(_to_ndvi)
        params = {"band": "NDVI", "unit": "NDVI"}
        return ic, params

    raise ValueError(f"Unsupported satellite for NDVI: {satellite}. Use MODIS, Landsat 8 & 9, SENTINEL")


def compute_period_feature_ndvi(
    start: ee.Date,
    collection: ee.ImageCollection,
    geometry: ee.Geometry,
    frequency: str,
    satellite: str,
    scale: Optional[int] = None,
) -> ee.Feature:
    """
    Compute the mean NDVI over a specified time period and spatial region.

    This function aggregates NDVI values from an ImageCollection over a given temporal interval 
    (weekly, monthly, or yearly) and computes the spatial mean across a provided geometry.

    Parameters
    ----------
    start : ee.Date
        Start date of the aggregation period.
    collection : ee.ImageCollection
        An ImageCollection containing a single "NDVI" band with values in the range [-1, 1].
    geometry : ee.Geometry
        Region of interest over which to compute the spatial mean.
    frequency : {"weekly", "monthly", "yearly"}
        Temporal aggregation interval. Determines the end date of the period.
    satellite : str
        Satellite name used to infer default spatial resolution if `scale` is not provided. 
        Supported: "MODIS", "LANDSAT", "SENTINEL", "SENTINEL2", or "S2".
    scale : int, optional
        Spatial resolution (in meters) for the reduction. If omitted, a sensor-appropriate 
        default is used (MODIS: 250 m, Landsat: 30 m, Sentinel-2: 10 m).

    Returns
    -------
    ee.Feature
        A feature with no geometry and two properties:
        - "date": Start date of the period formatted as "YYYY-MM-dd".
        - "ndvi_mean": Mean NDVI value over the geometry during the period. 
          Set to `null` if no valid pixels are available.

    Raises
    ------
    ValueError
        If `frequency` is not supported or if `satellite` is unknown and `scale` is not provided.

    Notes
    -----
    - Uses `ee.Reducer.mean()` with a high `maxPixels` limit (1e13) to support large regions.
    - Temporal period boundaries are defined using Earth Engine’s calendar-aware `advance()` method.
    - The input collection must already be processed to contain only the "NDVI" band.
    """

    if scale is None:
        sat = satellite.upper()
        default_scales = {
            "MODIS": 250, 
            "LANDSAT": 30, 
            "SENTINEL": 10, 
            "SENTINEL2": 10,
            "S2": 10,
        }
        if sat not in default_scales:
            raise ValueError(f"Unknown satellite for default scale: {satellite}")
        scale = default_scales[sat]

    ndvi_val = compute_period(
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
            "ndvi_mean": ndvi_val,
        },
    )


def compute_ndvi_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    """
    Compute a time series of mean Normalized Difference Vegetation Index (NDVI) over a region 
    of interest using Google Earth Engine.

    The function retrieves NDVI data from a specified satellite sensor, aggregates it over 
    regular time intervals (weekly, monthly, or yearly), and returns the results as a pandas DataFrame.

    Parameters
    ----------
    start_date : str
        Start date of the time series in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time series in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite data source. Supported options: 
        - "MODIS" (MOD13Q1)
        - "LANDSAT" (Landsat 8 & 9 Collection 2 Level 2 SR)
        - "SENTINEL", "SENTINEL2", or "S2" (Sentinel-2 SR Harmonized)
        (default: "MODIS").
    frequency : str, optional
        Temporal aggregation frequency. Must be one of: "weekly", "monthly", or "yearly" 
        (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        Must be provided; otherwise, a ValueError is raised.
    scale : int, optional
        Spatial resolution (in meters) for the reduction operation. If not provided, 
        a sensor-appropriate default is used (MODIS: 250 m, Landsat: 30 m, Sentinel-2: 10 m).

    Returns
    -------
    pd.DataFrame
        A DataFrame with the following columns:
        - "date": Start date of each period as "YYYY-MM-dd".
        - "ndvi_mean": Mean NDVI value (range [-1, 1]) over the ROI during that period.
        - "satellite": Name of the satellite used (uppercase).
        - "unit": Unit identifier (always "NDVI").
        Periods with no valid NDVI data (e.g., due to clouds or missing imagery) are excluded.

    Raises
    ------
    ValueError
        If `roi_gdf` is not provided or if `frequency` is invalid.

    Notes
    -----
    - Internally uses `get_ndvi_collection` to fetch and preprocess NDVI data, including cloud masking.
    - The collection is pre-filtered to the ROI using `filterBounds` to improve performance.
    - Time steps are approximated using fixed day counts (7, 30, or 365 days); calendar alignment 
      may vary slightly for monthly/yearly intervals.
    """

    if roi_gdf is None:
        raise ValueError("Provide roi_gdf (Region of Interest)")

    ensure_ee_initialized()
    geometry = gdf_to_ee_geometry(roi_gdf)

    collection, params = get_ndvi_collection(satellite, start_date, end_date)
    collection = collection.filterBounds(geometry)

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
        dates.map(lambda d: compute_period_feature_ndvi(
            ee.Date(d),
            collection,
            geometry,
            freq,
            satellite,
            scale=scale
        ))
    )

    features_info = features.getInfo()["features"]
    rows = [
        {
            "date": f["properties"]["date"],
            "ndvi_mean": f["properties"].get("ndvi_mean"),
            "satellite": satellite.upper(),
            "unit": params.get("unit", "NDVI"),
        }
        for f in features_info
        if f["properties"].get("ndvi_mean") is not None
    ]

    return pd.DataFrame(rows)


