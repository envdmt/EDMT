import ee 
import geopandas as gpd
import pandas as pd
from typing import Optional, Tuple, Literal
from edmt.analysis import (
    ee_initialized,
    gdf_to_ee_geometry,
    Reducer,
)

Frequency = Literal["daily", "weekly", "monthly", "yearly"]

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


def compute_period_chirps(
    start: ee.Date,
    collection: ee.ImageCollection,
    geometry: ee.Geometry,
    frequency: Frequency = "monthly",
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
    frequency: Frequency = "monthly",
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
            lambda d: compute_per_period_chirps(
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


def get_chirps_image(
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["sum", "mean", "median", "min", "max"] = "sum",
) -> ee.Image:
    """
    Generate a single composite precipitation image from the CHIRPS daily dataset over a specified time period.

    This function retrieves CHIRPS daily rainfall data, aggregates it using a specified reducer 
    (e.g., sum, mean), and optionally clips the result to a region of interest. The output is suitable 
    for visualization or further analysis in Earth Engine.

    Parameters
    ----------
    start_date : str
        Start date of the aggregation period in 'YYYY-MM-DD' format.
    end_date : str
        End date of the aggregation period in 'YYYY-MM-DD' format.
    frequency : {"daily", "weekly", "monthly", "yearly"}, optional
        Temporal interval type (used only for metadata labeling; does not affect computation).
    roi_gdf : geopandas.GeoDataFrame, optional
        Region of interest as a GeoDataFrame containing Polygon or MultiPolygon geometries. 
        If provided, the collection is filtered to this region and the output is clipped to it.
    reducer : {"sum", "mean", "median", "min", "max"}, optional
        Temporal aggregation method:
        - "sum": Total precipitation over the period (unit: mm)
        - Other reducers: Average or extreme daily rate (unit: mm/day)
        (default: "sum")

    Returns
    -------
    ee.Image
        A single-band image with band name `"precipitation_mm"` and the following properties:
        - "start": Input start date
        - "end": Input end date
        - "frequency": Aggregation frequency label
        - "reducer": Reducer used
        - "unit": "mm" if reducer is "sum", otherwise "mm/day"

    Notes
    -----
    - When `reducer="sum"`, the result represents **total accumulated rainfall** (in mm) over the period.
    - For other reducers (e.g., "mean"), the result represents a **statistic of daily rainfall rates** (in mm/day).
    - If `roi_gdf` is provided, the collection is pre-filtered with `filterBounds` for efficiency.
    - The output band is always renamed to `"precipitation_mm"` for consistency, regardless of unit.
    - Requires an initialized Earth Engine session (`ee.Initialize()`).
    """
    ee_initialized()

    roi: Optional[ee.Geometry] = None
    if roi_gdf is not None:
        roi = gdf_to_ee_geometry(roi_gdf)

    collection, _params = get_chirps_collection(start_date, end_date)

    if roi is not None:
        collection = collection.filterBounds(roi)

    collection = collection.select(["precipitation"], ["precipitation"])

    img = collection.sum().rename("precipitation_mm")
    unit = "mm"

    if roi is not None:
        img = img.clip(roi)

    img = img.set(
        {
            "start": start_date,
            "end": end_date,
            "frequency": frequency,
            "reducer": reducer,
            "unit": unit,
        }
    )

    return img


def compute_chirps_imgcoll(
    start: ee.Date,
    frequency: Literal["daily", "weekly", "monthly", "yearly"],
    collection: ee.ImageCollection,
    roi: Optional[ee.Geometry] = None,
) -> ee.Image:
    """
    Generate a single composite precipitation image from CHIRPS daily data over a specified time period.

    This helper function aggregates daily CHIRPS precipitation images within a temporal window 
    (daily, weekly, monthly, or yearly) by summing them to produce total accumulated rainfall (in mm), 
    and attaches metadata for time series applications.

    Parameters
    ----------
    start : ee.Date
        Start date of the aggregation period.
    frequency : {"daily", "weekly", "monthly", "yearly"}
        Temporal interval defining the period length. Determines the end date via Earth Engine’s 
        calendar-aware `advance()` method.
    collection : ee.ImageCollection
        CHIRPS daily precipitation ImageCollection with a "precipitation" band in mm/day.
    roi : ee.Geometry, optional
        Region of interest for clipping the output image. If provided, the result is spatially bounded.

    Returns
    -------
    ee.Image
        A single-band image with band name `"precipitation_mm"` representing total precipitation (mm) 
        over the period, and the following properties:
        - `"system:time_start"`: Period start in milliseconds since Unix epoch
        - `"period_start"`: Formatted as "YYYY-MM-dd"
        - `"period_end"`: End of the period (exclusive) as "YYYY-MM-dd"
        - `"frequency"`: Aggregation frequency used
        - `"unit"`: Always "mm" (total accumulation)
        - `"dataset"`: Source dataset identifier
        - `"n_images"`: Number of daily images included in the sum

    Raises
    ------
    ValueError
        If `frequency` is not one of the supported options.

    """
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
        raise ValueError("frequency must be one of: daily, weekly, monthly, yearly")

    period_ic = collection.filterDate(start, end).select(["precipitation"], ["precipitation"])
    n_images = period_ic.size()

    img = period_ic.sum().rename("precipitation_mm")

    img = img.set(
        {
            "system:time_start": start.millis(),
            "period_start": start.format("YYYY-MM-dd"),
            "period_end": end.format("YYYY-MM-dd"),
            "frequency": frequency,
            "unit": "mm",
            "dataset": "UCSB-CHG/CHIRPS/DAILY",
            "n_images": n_images,
        }
    )

    if roi is not None:
        img = img.clip(roi)

    return img


def get_chirps_image_collection(
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
) -> ee.ImageCollection:
    """
    Generate an Earth Engine ImageCollection of CHIRPS precipitation composites aggregated over
    regular time periods (daily, weekly, monthly, yearly).

    Each image represents TOTAL precipitation for the period (mm), with:
      - band: "precipitation_mm"
      - system:time_start set to period start
      - properties: period_start, period_end, frequency, unit, n_images

    Parameters
    ----------
    start_date, end_date : str
        Overall time window in 'YYYY-MM-DD'.
    frequency : {"daily","weekly","monthly","yearly"}
        Temporal aggregation interval (default: "monthly").
    roi_gdf : GeoDataFrame, optional
        ROI to filterBounds + clip composites.

    Returns
    -------
    ee.ImageCollection
        Period composites of CHIRPS precipitation totals (mm).
    """
    ee_initialized()

    roi: Optional[ee.Geometry] = None
    if roi_gdf is not None:
        roi = gdf_to_ee_geometry(roi_gdf)

    collection, _ = get_chirps_collection(start_date, end_date)

    if roi is not None:
        collection = collection.filterBounds(roi)

    freq = frequency.lower()
    if freq not in {"daily", "weekly", "monthly", "yearly"}:
        raise ValueError("frequency must be one of: daily, weekly, monthly, yearly")

    step_days = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}[freq]
    dates = ee.List.sequence(
        ee.Date(start_date).millis(),
        ee.Date(end_date).millis(),
        step_days * 24 * 60 * 60 * 1000,
    )

    return ee.ImageCollection(
        dates.map(lambda d: compute_chirps_imgcoll(ee.Date(d), freq, collection, roi))
    )





