from typing import Optional
import geopandas as gpd
import pandas as pd
import ee
from typing import Literal
from .connector import (
    compute_timeseries,
    get_product_image,
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


def compute_ndvi_evi_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:
    return compute_timeseries(
        product="NDVI_EVI",
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


def get_lst_image(
    start_date: str,
    end_date: str,
    satellite: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:
  return get_product_image(
      "LST",
      start_date,
      end_date,
      satellite=satellite,
      roi_gdf=roi_gdf,
      reducer=reducer
      )


def get_ndvi_image(
    start_date: str,
    end_date: str,
    satellite: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:

      return get_product_image("NDVI", start_date, end_date, satellite=satellite, roi_gdf=roi_gdf, reducer=reducer)


def get_evi_image(
    start_date: str,
    end_date: str,
    satellite: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:
    return get_product_image("EVI", start_date, end_date, satellite=satellite, roi_gdf=roi_gdf, reducer=reducer)


def get_chirps_image(
    start_date: str,
    end_date: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: Literal["mean", "median", "min", "max"] = "mean",
) -> ee.Image:
    return get_product_image("CHIRPS", start_date, end_date, satellite=None, roi_gdf=roi_gdf, reducer=reducer)















