import ee 
import geopandas as gpd
import pandas as pd
from typing import Optional, Tuple
from edmt.analysis import (
    ee_initialized,
    compute_period,
    gdf_to_ee_geometry,
    _ndvi_from_nir_red,
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
    Raw data is scaled appropriately per sensor, and basic quality filtering is applied where needed.

    Parameters
    ----------
    satellite : str
        Satellite platform or product name. Supported options:
        - "LANDSAT", "LANDSAT_8DAY", or "LANDSAT8DAY": Uses precomputed 8-day Landsat NDVI composites 
          (Collection 2 Tier 1).
        - "MODIS": Uses MOD13Q1 (16-day L3 global 250m); values scaled by 0.0001.
        - "SENTINEL", "SENTINEL2", or "S2": Uses Sentinel-2 Harmonized (COPERNICUS/S2_HARMONIZED); 
          reflectance divided by 10,000; images with >60% cloud cover are excluded.
        - "VIIRS", "NOAA_VIIRS", or "NOAA": Uses NOAA CDR VIIRS NDVI V1; invalid values (-9998) masked, 
          values scaled by 0.0001.
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

    if sat in ("LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY"):
      ic = (
          ee.ImageCollection("LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI")
          .filterDate(start_date, end_date)
      )
      ic = ic.select(["NDVI"], ["NDVI"]).map(
          lambda img: img.copyProperties(img, ["system:time_start"])
      )
      return ic, {"band": "NDVI", "unit": "NDVI"}

    if sat == "MODIS":
      scale = 250
      ic = (
          ee.ImageCollection("MODIS/061/MOD13Q1")
          .filterDate(start_date, end_date)
          .select("NDVI")
          .map(
              lambda img: img
                  .multiply(0.0001)
                  .rename("NDVI")
                  .copyProperties(img, ["system:time_start"])
          ))

      return ic, {"band": "NDVI", "unit": "NDVI"}

    if sat in ("SENTINEL", "SENTINEL2", "S2"):
      ic = (
          ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
          .filterDate(start_date, end_date)
          .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 60))
      )

      def _to_ndvi(img: ee.Image) -> ee.Image:
          red = img.select("B4").divide(10000.0)
          nir = img.select("B8").divide(10000.0)
          ndvi = _ndvi_from_nir_red(img, nir, red)
          return ndvi.copyProperties(img, ["system:time_start"])

      ic = ic.map(_to_ndvi)
      return ic, {"band": "NDVI", "unit": "NDVI"}

    if sat in ("VIIRS", "NOAA_VIIRS", "NOAA"):
      ic = (
          ee.ImageCollection("NOAA/CDR/VIIRS/NDVI/V1")
          .filterDate(start_date, end_date)
          .select("NDVI")
          .map(lambda img: (
              img
              .updateMask(img.neq(-9998))
              .multiply(0.0001)             
              .rename("NDVI")
              .copyProperties(img, ["system:time_start"])
          ))
      )
      return ic, {"band": "NDVI", "unit": "NDVI"}

    raise ValueError(
        f"Unsupported satellite for NDVI: {satellite}. "
        "Use LANDSAT, MODIS, SENTINEL2/S2, or VIIRS."
    )


def compute_period_feature_ndvi(
    start: ee.Date,
    collection: ee.ImageCollection,
    geometry: ee.Geometry,
    frequency: str,
    satellite: str,
    scale: Optional[int] = None,
) -> ee.Feature:
    """
    Compute the mean NDVI over a specified time period and spatial region, returning a feature with metadata.

    This function aggregates NDVI images within a temporal window (weekly, monthly, or yearly), computes 
    the spatial mean over a region of interest, and includes the number of contributing images.

    Parameters
    ----------
    start : ee.Date
        Start date of the aggregation period.
    collection : ee.ImageCollection
        An ImageCollection containing a band named "NDVI" with values in the range [-1, 1].
    geometry : ee.Geometry
        Region of interest over which to compute the spatial mean.
    frequency : {"weekly", "monthly", "yearly"}
        Temporal interval defining the period length. Determines the end date via Earth Engine’s 
        calendar-aware `advance()` method.
    satellite : str
        Satellite name used to infer default spatial resolution if `scale` is not provided. 
        Supported: "LANDSAT", "LANDSAT_8DAY", "MODIS", "SENTINEL2", "VIIRS", etc.
    scale : int, optional
        Spatial resolution (in meters) for the reduction. If omitted, a sensor-specific default is used:
        - Landsat products: 30 m
        - MODIS & VIIRS: 500 m
        - Sentinel-2: 10 m

    Returns
    -------
    ee.Feature
        A feature with no geometry and the following properties:
        - "date": Period start formatted as "YYYY-MM-dd"
        - "ndvi": Mean NDVI value over the geometry (or `null` if no valid pixels)
        - "n_images": Number of images in the period used for compositing

    Raises
    ------
    ValueError
        If `frequency` is not one of "weekly", "monthly", or "yearly".
        
    """

    if scale is None:
        sat = satellite.upper()
        default_scales = {
            "LANDSAT": 30,       
            "LANDSAT_8DAY": 30,
            "LANDSAT8DAY": 30,
            "MODIS": 500, 
            "SENTINEL": 10,
            "SENTINEL2": 10,
            "S2": 10,
            "VIIRS": 500,
            "NOAA_VIIRS": 500,
            "NOAA": 500,
        }
        scale = default_scales.get(sat, 30)

    start = ee.Date(start)
    if frequency == "weekly":
        end = start.advance(1, "week")
    elif frequency == "monthly":
        end = start.advance(1, "month")
    elif frequency == "yearly":
        end = start.advance(1, "year")
    else:
        raise ValueError(f"Invalid frequency: {frequency}")

    period_ic = collection.filterDate(start, end)

    def _empty():
        return ee.Feature(None, {
            "date": start.format("YYYY-MM-dd"),
            "ndvi": None,
            "n_images": 0,
        })

    def _compute():
        img = period_ic.select("NDVI").mean()
        proj = img.select("NDVI").projection()
        geom_in_img_crs = geometry.transform(proj, 1)

        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom_in_img_crs,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
        )

        return ee.Feature(None, {
            "date": start.format("YYYY-MM-dd"),
            "ndvi": stats.get("NDVI"),
            "n_images": period_ic.size(),
        })

    return ee.Feature(ee.Algorithms.If(period_ic.size().gt(0), _compute(), _empty()))


def compute_ndvi_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "LANDSAT",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    """
    Compute a time series of mean NDVI values over a region of interest using Google Earth Engine.

    This function retrieves preprocessed NDVI data from a specified satellite product, aggregates 
    it over regular time intervals (weekly, monthly, or yearly), and computes the spatial mean for 
    each period. It also reports the number of images used per period.

    Parameters
    ----------
    start_date : str
        Start date of the time series in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time series in 'YYYY-MM-DD' format.
    satellite : str, optional
        Satellite or product name. Supported options:
        - "LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY": 8-day Landsat NDVI composites
        - "MODIS": MOD13Q1 (16-day, 250m)
        - "SENTINEL", "SENTINEL2", "S2": Sentinel-2 Harmonized
        - "VIIRS", "NOAA_VIIRS", "NOAA": NOAA CDR VIIRS NDVI
        (default: "LANDSAT").
    frequency : {"weekly", "monthly", "yearly"}, optional
        Temporal aggregation interval (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        Must be provided; otherwise, a ValueError is raised.
    scale : int, optional
        Spatial resolution (in meters) for reduction. If omitted, a sensor-specific default is used:
        - Landsat: 30 m
        - MODIS & VIIRS: 500 m
        - Sentinel-2: 10 m

    Returns
    -------
    pd.DataFrame
        A DataFrame with one row per time period, containing:
        - "date": Period start as "YYYY-MM-dd"
        - "ndvi": Mean NDVI value (range [-1, 1]); `NaN` if no valid data
        - "n_images": Number of source images contributing to the period composite
        - "satellite": Uppercase satellite/product name
        - "unit": Always "NDVI"

    Raises
    ------
    ValueError
        If `roi_gdf` is not provided or if `frequency` is invalid.

    """

    ee_initialized()

    if roi_gdf is None:
        raise ValueError("Provide roi_gdf (Region of Interest)")

    geometry = gdf_to_ee_geometry(roi_gdf)
    collection, params = get_ndvi_collection(satellite, start_date, end_date)

    if satellite.upper() == "MODIS":
        proj = ee.Image(collection.first()).select("NDVI").projection()
        geometry = geometry.transform(proj, 1)

    collection = collection.filterBounds(geometry)

    freq = frequency.lower()
    unit = {"weekly": "week", "monthly": "month", "yearly": "year"}.get(freq)
    if unit is None:
        raise ValueError("frequency must be one of: weekly, monthly, yearly")

    start_ee = ee.Date(start_date)
    end_ee = ee.Date(end_date)
    n = end_ee.difference(start_ee, unit).floor()

    dates = ee.List.sequence(0, n).map(lambda i: start_ee.advance(ee.Number(i), unit))

    fc = ee.FeatureCollection(
        dates.map(lambda d: compute_period_feature_ndvi(
            ee.Date(d),
            collection,
            geometry,
            freq,
            satellite,
            scale=scale,
        ))
    )

    feats = fc.getInfo()["features"]
    rows = []
    for f in feats:
        p = f["properties"]
        rows.append({
            "date": p["date"],
            "ndvi": p.get("ndvi"),
            "n_images": p.get("n_images"),
            "satellite": satellite.upper(),
            "unit": params.get("unit", "NDVI"),
        })

    return pd.DataFrame(rows)


