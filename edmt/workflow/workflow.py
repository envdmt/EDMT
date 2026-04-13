from typing import Optional
import geopandas as gpd
import pandas as pd
import ee
from .connector import (
    ComputeTimeseries,
    CompositeImage,
    CollectionImage,
)
from .builder import (
    Frequency,
    ReducerName,
)

def compute_lst_timeseries(
    start_date: str,
    end_date: str,
    satellite: str = "MODIS",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:

    return ComputeTimeseries(
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
    satellite: str = "LANDSAT8",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:

    return ComputeTimeseries(
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
    end_date: str,
    satellite: str = "Sentinel2",
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:

    return ComputeTimeseries(
        product="EVI",
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
    frequency: str = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    scale: Optional[int] = None,
) -> pd.DataFrame:

    return ComputeTimeseries(
        product="CHIRPS",
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        roi_gdf=roi_gdf,
        satellite=None
    )


def get_lst_image(
    start_date: str,
    end_date: str,
    satellite: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.Image:
  return CompositeImage(
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
    reducer: ReducerName = "mean",
) -> ee.Image:

      return CompositeImage(
          "NDVI", 
          start_date, 
          end_date, 
          satellite=satellite, 
          roi_gdf=roi_gdf, 
          reducer=reducer
          )


def get_evi_image(
    start_date: str,
    end_date: str,
    satellite: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.Image:
    return CompositeImage(
        "EVI", 
        start_date, 
        end_date, 
        satellite=satellite, 
        roi_gdf=roi_gdf, 
        reducer=reducer
        )


def get_chirps_image(
    start_date: str,
    end_date: str,
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "max",
) -> ee.Image:
    return CompositeImage(
        "CHIRPS", 
        start_date, 
        end_date, 
        satellite=None, 
        roi_gdf=roi_gdf, 
        reducer=reducer
        )


def get_lst_image_collection(
    start_date: str,
    end_date: str,
    satellite: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.ImageCollection:
    return CollectionImage(
        "LST", 
        start_date, 
        end_date, 
        satellite=satellite, 
        frequency=frequency,
        roi_gdf=roi_gdf, 
        reducer=reducer
        )


def get_ndvi_image_collection(
    start_date: str,
    end_date : str,
    satellite: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.ImageCollection:
    return CollectionImage(
        "NDVI", 
        start_date, 
        end_date, 
        satellite=satellite, 
        frequency=frequency, 
        roi_gdf=roi_gdf, 
        reducer=reducer
        )


def get_evi_image_collection(
    start_date: str,
    end_date: str,
    satellite: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "mean",
) -> ee.ImageCollection:
    return CollectionImage(
        "EVI", 
        start_date, 
        end_date, 
        satellite=satellite, 
        frequency=frequency, 
        roi_gdf=roi_gdf, 
        reducer=reducer
        )


def get_chirps_image_collection(
    start_date: str,
    end_date: str,
    frequency: Frequency = "monthly",
    roi_gdf: Optional[gpd.GeoDataFrame] = None,
    reducer: ReducerName = "max",
) -> ee.ImageCollection:
    return CollectionImage(
        "CHIRPS", 
        start_date, 
        end_date, 
        frequency=frequency, 
        satellite=None, 
        roi_gdf=roi_gdf, 
        reducer=reducer
        )








