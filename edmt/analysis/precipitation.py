import ee 
import geopandas as gpd
import pandas as pd
from typing import Optional, Tuple, Literal
from edmt.analysis import (
    ee_initialized,
    gdf_to_ee_geometry,
)

def get_chirps_collection(
    start_date: str,
    end_date: str,
) -> Tuple[ee.ImageCollection, dict]:
    """
    Retrieve the CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data) daily 
    precipitation ImageCollection from Google Earth Engine.

    CHIRPS is a quasi-global rainfall dataset spanning 1981–present, combining satellite imagery 
    with in-situ station data to provide high-resolution precipitation estimates.

    Parameters
    ----------
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.

    Returns
    -------
    tuple[ee.ImageCollection, dict]
        - **ImageCollection**: Daily precipitation images filtered to the specified date range, 
          with the band renamed to "precipitation" and original time metadata preserved.
        - **params**: Dictionary with keys:
            - "band": Name of the precipitation band ("precipitation")
            - "unit": Unit of measurement ("mm")
    """
    ic = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(start_date, end_date)
        .select("precipitation")
        .map(lambda img: img.copyProperties(img, ["system:time_start"]))
    )
    return ic, {"band": "precipitation", "unit": "mm"}


def compute_period_feature_chirps(
    start: ee.Date,
    collection: ee.ImageCollection,
    geometry: ee.Geometry,
    frequency: Literal["daily", "weekly", "monthly", "yearly"] = "monthly",
    scale: Optional[int] = None,
) -> ee.Feature:
    """
    Compute total precipitation over a specified time period from CHIRPS daily data and return 
    a feature with spatial mean and metadata.

    This function aggregates daily precipitation images within a temporal window (daily, weekly, 
    monthly, or yearly), sums them to get cumulative rainfall, and computes the spatial mean 
    over a region of interest.

    Parameters
    ----------
    start : ee.Date
        Start date of the aggregation period.
    collection : ee.ImageCollection
        CHIRPS daily precipitation ImageCollection with a "precipitation" band in mm/day.
    geometry : ee.Geometry
        Region of interest over which to compute the spatial mean of total precipitation.
    frequency : {"daily", "weekly", "monthly", "yearly"}, optional
        Temporal interval defining the period length (default: "monthly").
    scale : int, optional
        Spatial resolution (in meters) for the reduction. If omitted, defaults to 5000 m 
        (appropriate for CHIRPS' ~5 km native resolution).

    Returns
    -------
    ee.Feature
        A feature with no geometry and the following properties:
        - "date": Period start formatted as "YYYY-MM-dd"
        - "precipitation_mm": Spatial mean of cumulative precipitation (in mm) over the period
        - "n_images": Number of daily images used in the sum

    Raises
    ------
    ValueError
        If `frequency` is not one of the supported options.

    Notes
    -----
    - **Aggregation logic**: Daily values are summed first (to get total mm over the period), 
      then the spatial mean of that total is computed.
    - For "daily" frequency, the result is equivalent to the spatial mean of a single day’s precipitation.
    - Uses `bestEffort=True` in `reduceRegion` to handle large geometries.
    - Geometry is reprojected to the image’s native CRS (WGS84) before reduction.
    - Periods with no data return `"precipitation_mm": null` and `"n_images": 0`.
    - Designed for use in mapping over date sequences to build precipitation time series.
    """

    if scale is None:
        scale = 5000

    start = ee.Date(start)

    if frequency == "daily":
        end = start.advance(1, "day")
    elif frequency == "weekly":
        end = start.advance(1, "week")
    elif frequency == "monthly":
        end = start.advance(1, "month")
    elif frequency == "yearly":
        end = start.advance(1, "year")
    else:
        raise ValueError(f"Invalid frequency: {frequency}")

    period_ic = collection.filterDate(start, end)

    def _empty():
        return ee.Feature(
            None,
            {
                "date": start.format("YYYY-MM-dd"),
                "precipitation_mm": None,
                "n_images": 0,
            },
        )

    def _compute():
        img = period_ic.select("precipitation").sum()

        proj = img.select("precipitation").projection()
        geom_in_img_crs = geometry.transform(proj, 1)

        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),  
            geometry=geom_in_img_crs,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
        )

        return ee.Feature(
            None,
            {
                "date": start.format("YYYY-MM-dd"),
                "precipitation_mm": stats.get("precipitation"),
                "n_images": period_ic.size(),
            },
        )

    return ee.Feature(ee.Algorithms.If(period_ic.size().gt(0), _compute(), _empty()))


def compute_chirps_timeseries(
    start_date: str,
    end_date: str,
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    """
    Compute a time series of spatially averaged precipitation totals from the CHIRPS daily dataset 
    over a user-defined region of interest.

    This function retrieves CHIRPS (Climate Hazards Group InfraRed Precipitation with Station data) 
    daily rainfall estimates, aggregates them over regular time intervals (daily, weekly, monthly, or yearly), 
    and computes the spatial mean of cumulative precipitation for each period.

    Parameters
    ----------
    start_date : str
        Start date of the time series in 'YYYY-MM-DD' format.
    end_date : str
        End date of the time series in 'YYYY-MM-DD' format.
    frequency : {"daily", "weekly", "monthly", "yearly"}, optional
        Temporal aggregation interval (default: "monthly").
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        Must be provided; otherwise, a ValueError is raised.
    scale : int, optional
        Spatial resolution (in meters) for the reduction operation. If omitted, defaults to 5000 m, 
        matching CHIRPS' native ~5 km resolution.

    Returns
    -------
    pd.DataFrame
        A DataFrame with one row per time period, containing:
        - "date": Period start as "YYYY-MM-dd"
        - "precipitation_mm": Spatial mean of total precipitation (in mm) over the period
        - "n_images": Number of daily CHIRPS images used in the sum
        - "satellite": Always "CHIRPS"
        - "unit": Always "mm"

    Raises
    ------
    ValueError
        If `roi_gdf` is not provided or if `frequency` is invalid.

    """
    ee_initialized()

    if roi_gdf is None:
        raise ValueError("Provide roi_gdf (Region of Interest)")

    geometry = gdf_to_ee_geometry(roi_gdf)

    collection, params = get_chirps_collection(start_date, end_date)

    collection = collection.filterBounds(geometry)

    freq = frequency.lower()
    unit = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",
    }.get(freq)

    if unit is None:
        raise ValueError("frequency must be one of: daily, weekly, monthly, yearly")

    start_ee = ee.Date(start_date)
    end_ee = ee.Date(end_date)
    n = end_ee.difference(start_ee, unit).floor()

    dates = ee.List.sequence(0, n).map(lambda i: start_ee.advance(ee.Number(i), unit))

    fc = ee.FeatureCollection(
        dates.map(
            lambda d: compute_period_feature_chirps(
                ee.Date(d),
                collection,
                geometry,
                freq,
                scale=scale,
            )
        )
    )

    feats = fc.getInfo()["features"]
    rows = []
    for f in feats:
        p = f["properties"]
        rows.append(
            {
                "date": p["date"],
                "precipitation_mm": p.get("precipitation_mm"),
                "n_images": p.get("n_images"),
                "satellite": "CHIRPS",
                "unit": params.get("unit", "mm"),
            }
        )

    return pd.DataFrame(rows)





