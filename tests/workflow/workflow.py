from typing import Optional
import geopandas as gpd
import pandas as pd
from .connector import (
    compute_timeseries
)
from .builder import (
    Frequency
)

def compute_lst_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    return compute_timeseries(
        product="LST",
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        roi_gdf=roi_gdf,
        satellite=satellite,
        scale=scale,
    )


def compute_ndvi_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "LANDSAT",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    return compute_timeseries(
        product="NDVI",
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        roi_gdf=roi_gdf,
        satellite=satellite,
        scale=scale,
    )


def compute_evi_timeseries(
    start_date: str,
    product: str,
    end_date: str,
    satellite: str = "S2", 
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    return compute_timeseries(
        product=product,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        roi_gdf=roi_gdf,
        satellite=satellite,
        scale=scale,
    )


def compute_chirps_timeseries(
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    return compute_timeseries(
        product="CHIRPS",
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        roi_gdf=roi_gdf,
        satellite=None,
        scale=scale,
    )
