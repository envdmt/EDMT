import ee
import geopandas as gpd
import pandas as pd
import shapely
from typing import Any, Dict, Literal, Optional, Tuple
from __future__ import annotations


Frequency = Literal["daily", "weekly", "monthly", "yearly"]

def ee_initialized():
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



def _norm(x: Optional[str]) -> str:
    return (x or "").strip().upper().replace("-", "_").replace(" ", "_")


def _copy_time(img: ee.Image) -> ee.Image:
    return img.copyProperties(img, ["system:time_start"])


def _ndvi_from_nir_red(nir: ee.Image, red: ee.Image) -> ee.Image:
    return nir.subtract(red).divide(nir.add(red)).rename("NDVI")


def _evi_from_nir_red_blue(nir: ee.Image, red: ee.Image, blue: ee.Image) -> ee.Image:
    # EVI = 2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)
    num = nir.subtract(red).multiply(2.5)
    den = nir.add(red.multiply(6.0)).subtract(blue.multiply(7.5)).add(1.0)
    return num.divide(den).rename("EVI")


def _advance_end(start: ee.Date, frequency: str) -> ee.Date:
    f = frequency.lower()
    if f == "daily":
        return start.advance(1, "day")
    if f == "weekly":
        return start.advance(1, "week")
    if f == "monthly":
        return start.advance(1, "month")
    if f == "yearly":
        return start.advance(1, "year")
    raise ValueError(f"Invalid frequency: {frequency}")


def _empty(
    prod: str,
    start: ee.Date,
) -> ee.Feature:
    base = {
        "date": start.format("YYYY-MM-dd"),
        "product": prod,
        "n_images": 0,
    }

    if prod == "CHIRPS":
        base["precipitation_mm"] = None
    elif prod in ("NDVI", "EVI"):
        base[prod.lower()] = None
    elif prod == "LST":
        base.update({"mean": None, "median": None, "min": None, "max": None})
    else:
        base["value"] = None
    return ee.Feature(None, base)



# ----------------------------
# Builders (return (ic, meta)) 
# (public entry function)
# ----------------------------
def _build_lst(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    sat = _norm(satellite)

    if sat == "MODIS":
        ic = (
            ee.ImageCollection("MODIS/061/MOD11A1")
            .filterDate(start_date, end_date)
            .select(["LST_Day_1km"], ["LST_Day_1km"])
            .map(_copy_time)
        )
        meta = {
            "product": "LST",
            "band": "LST_Day_1km",
            "unit": "K",
            # "unit": "°C",
            "multiply": 0.02,
            "add": 0.0,
            "scale_m": 1000,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
        }
        return ic, meta

    if sat in ("LANDSAT8", "LANDSAT_8", "LC08"):
        ic = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterDate(start_date, end_date)
            .select(["ST_B10"], ["ST_B10"])
            .map(_copy_time)
        )
        meta = {
            "product": "LST",
            "band": "ST_B10",
            "unit": "K",
            "multiply": 0.00341802,
            "add": 149.0,
            "scale_m": 30,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
        }
        return ic, meta

    if sat in ("LANDSAT9", "LANDSAT_9", "LC09"):
        ic = (
            ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
            .filterDate(start_date, end_date)
            .select(["ST_B10"], ["ST_B10"])
            .map(_copy_time)
        )
        meta = {
            "product": "LST",
            "band": "ST_B10",
            "unit": "K",
            "multiply": 0.00341802,
            "add": 149.0,
            "scale_m": 30,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
        }
        return ic, meta

    if sat == "GCOM":
        ic = (
            ee.ImageCollection("JAXA/GCOM-C/L3/LAND/LST/V3")
            .filterDate(start_date, end_date)
            .select(["LST_AVE"], ["LST_AVE"])
            .map(_copy_time)
        )
        meta = {
            "product": "LST",
            "band": "LST_AVE",
            "unit": "K",
            "multiply": 0.02,
            "add": 0.0,
            "scale_m": 5000,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
        }
        return ic, meta

    raise ValueError(f"Unsupported satellite for LST: {satellite}. Use MODIS, LANDSAT8/9, or GCOM.")



def _build_ndvi(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    sat = _norm(satellite)

    if sat in ("LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY"):
        ic = (
            ee.ImageCollection("LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI")
            .filterDate(start_date, end_date)
            .select(["NDVI"], ["NDVI"])
            .map(_copy_time)
        )
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 30,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat == "MODIS":
        ic = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select(["NDVI"], ["NDVI"])
            .map(lambda img: img.multiply(0.0001).rename("NDVI").copyProperties(img, ["system:time_start"]))
        )
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 250,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("SENTINEL", "SENTINEL2", "S2"):
        base = (
            ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 60))
        )

        def _to_ndvi(img: ee.Image) -> ee.Image:
            red = img.select("B4").divide(10000.0)
            nir = img.select("B8").divide(10000.0)
            ndvi = _ndvi_from_nir_red(nir, red)
            return ndvi.copyProperties(img, ["system:time_start"])

        ic = base.map(_to_ndvi)
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 10,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("VIIRS", "NOAA_VIIRS", "NOAA"):
        ic = (
            ee.ImageCollection("NOAA/CDR/VIIRS/NDVI/V1")
            .filterDate(start_date, end_date)
            .select(["NDVI"], ["NDVI"])
            .map(lambda img: (
                img.updateMask(img.neq(-9998))
                   .multiply(0.0001)
                   .rename("NDVI")
                   .copyProperties(img, ["system:time_start"])
            ))
        )
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 500,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    raise ValueError(f"Unsupported satellite for NDVI: {satellite}. Use LANDSAT8DAY, MODIS, S2, or VIIRS.")



def _build_lst(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    sat = _norm(satellite)

    if sat in ("LANDSAT", "LANDSAT_8DAY", "LANDSAT8DAY"):
        ic = (
            ee.ImageCollection("LANDSAT/COMPOSITES/C02/T1_L2_8DAY_NDVI")
            .filterDate(start_date, end_date)
            .select(["NDVI"], ["NDVI"])
            .map(_copy_time)
        )
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 30,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat == "MODIS":
        ic = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select(["NDVI"], ["NDVI"])
            .map(lambda img: img.multiply(0.0001).rename("NDVI").copyProperties(img, ["system:time_start"]))
        )
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 250,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("SENTINEL", "SENTINEL2", "S2"):
        base = (
            ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 60))
        )

        def _to_ndvi(img: ee.Image) -> ee.Image:
            red = img.select("B4").divide(10000.0)
            nir = img.select("B8").divide(10000.0)
            ndvi = _ndvi_from_nir_red(nir, red)
            return ndvi.copyProperties(img, ["system:time_start"])

        ic = base.map(_to_ndvi)
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 10,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("VIIRS", "NOAA_VIIRS", "NOAA"):
        ic = (
            ee.ImageCollection("NOAA/CDR/VIIRS/NDVI/V1")
            .filterDate(start_date, end_date)
            .select(["NDVI"], ["NDVI"])
            .map(lambda img: (
                img.updateMask(img.neq(-9998))
                   .multiply(0.0001)
                   .rename("NDVI")
                   .copyProperties(img, ["system:time_start"])
            ))
        )
        return ic, {
            "product": "NDVI",
            "bands": ["NDVI"],
            "unit": "NDVI",
            "scale_m": 500,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    raise ValueError(f"Unsupported satellite for NDVI: {satellite}. Use LANDSAT8DAY, MODIS, S2, or VIIRS.")



def _build_evi(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    sat = _norm(satellite)

    if sat == "MODIS":
        ic = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select(["EVI"], ["EVI"])
            .map(lambda img: img.multiply(0.0001).rename("EVI").copyProperties(img, ["system:time_start"]))
        )
        return ic, {
            "product": "EVI",
            "bands": ["EVI"],
            "unit": "EVI",
            "scale_m": 250,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("SENTINEL", "SENTINEL2", "S2"):
        base = (
            ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 60))
        )

        def _to_evi(img: ee.Image) -> ee.Image:
            blue = img.select("B2").divide(10000.0)
            red = img.select("B4").divide(10000.0)
            nir = img.select("B8").divide(10000.0)
            evi = _evi_from_nir_red_blue(nir, red, blue)
            return evi.copyProperties(img, ["system:time_start"])

        ic = base.map(_to_evi)
        return ic, {
            "product": "EVI",
            "bands": ["EVI"],
            "unit": "EVI",
            "scale_m": 10,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("LANDSAT8", "LANDSAT_8", "LC08", "LANDSAT9", "LANDSAT_9", "LC09"):
        col_id = "LANDSAT/LC08/C02/T1_L2" if sat in ("LANDSAT8", "LANDSAT_8", "LC08") else "LANDSAT/LC09/C02/T1_L2"

        base = (
            ee.ImageCollection(col_id)
            .filterDate(start_date, end_date)
        )

        # C2 L2 SR scale/offset
        # SR = DN * 0.0000275 + (-0.2)
        def _sr(img: ee.Image, band: str) -> ee.Image:
            return img.select(band).multiply(0.0000275).add(-0.2)

        def _to_evi(img: ee.Image) -> ee.Image:
            blue = _sr(img, "SR_B2")
            red  = _sr(img, "SR_B4")
            nir  = _sr(img, "SR_B5")
            evi = _evi_from_nir_red_blue(nir, red, blue)  # returns band named "EVI"
            return evi.copyProperties(img, ["system:time_start"])

        ic = base.map(_to_evi)
        return ic, {
            "product": "EVI",
            "bands": ["EVI"],
            "unit": "EVI",
            "scale_m": 30,
            "start_date": start_date,
            "end_date": end_date,
            "satellite": sat,
        }

    raise ValueError(
        f"Unsupported satellite for EVI: {satellite}. "
        "Use MODIS, SENTINEL2/S2, or LANDSAT8/9."
    )



def _build_ndvi_evi(satellite: str, start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    sat = _norm(satellite)

    if sat == "MODIS":
        ic = (
            ee.ImageCollection("MODIS/061/MOD13Q1")
            .filterDate(start_date, end_date)
            .select(["NDVI", "EVI"], ["NDVI", "EVI"])
            .map(lambda img: (
                img.multiply(0.0001)
                   .rename(["NDVI", "EVI"])
                   .copyProperties(img, ["system:time_start"])
            ))
        )
        return ic, {
            "product": "NDVI_EVI",
            "bands": ["NDVI", "EVI"],
            "unit": "index",
            "scale_m": 250,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("SENTINEL", "SENTINEL2", "S2"):
        base = (
            ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 60))
        )

        def _to_both(img: ee.Image) -> ee.Image:
            blue = img.select("B2").divide(10000.0)
            red = img.select("B4").divide(10000.0)
            nir = img.select("B8").divide(10000.0)
            ndvi = _ndvi_from_nir_red(nir, red)
            evi = _evi_from_nir_red_blue(nir, red, blue)
            out = ndvi.addBands(evi)
            return out.copyProperties(img, ["system:time_start"])

        ic = base.map(_to_both)
        return ic, {
            "product": "NDVI_EVI",
            "bands": ["NDVI", "EVI"],
            "unit": "index",
            "scale_m": 10,
            "start_date" : start_date,
            "end_date" : end_date,
            "satellite" : sat
            }

    if sat in ("LANDSAT8", "LANDSAT_8", "LC08", "LANDSAT9", "LANDSAT_9", "LC09"):
        col_id = "LANDSAT/LC08/C02/T1_L2" if sat in ("LANDSAT8", "LANDSAT_8", "LC08") else "LANDSAT/LC09/C02/T1_L2"

        base = (
            ee.ImageCollection(col_id)
            .filterDate(start_date, end_date)
        )

        # C2 L2 SR scale/offset: SR = DN * 0.0000275 + (-0.2)
        def _sr(img: ee.Image, band: str) -> ee.Image:
            return img.select(band).multiply(0.0000275).add(-0.2)

        def _to_both(img: ee.Image) -> ee.Image:
            blue = _sr(img, "SR_B2")
            red  = _sr(img, "SR_B4")
            nir  = _sr(img, "SR_B5")

            ndvi = _ndvi_from_nir_red(nir, red)           # "NDVI"
            evi  = _evi_from_nir_red_blue(nir, red, blue) # "EVI"

            out = ndvi.addBands(evi)
            return out.copyProperties(img, ["system:time_start"])

        ic = base.map(_to_both)
        return ic, {
            "product": "NDVI_EVI",
            "bands": ["NDVI", "EVI"],
            "unit": "index",
            "scale_m": 30,
            "start_date": start_date,
            "end_date": end_date,
            "satellite": sat,
        }

    raise ValueError(
        f"Unsupported satellite for NDVI_EVI: {satellite}. "
        "Use MODIS, SENTINEL2/S2, or LANDSAT8/9."
    )



def _build_chirps(start_date: str, end_date: str) -> Tuple[ee.ImageCollection, Dict[str, Any]]:
    ic = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(start_date, end_date)
        .select(["precipitation"], ["precipitation"])
        .map(_copy_time)
    )
    return ic, {
        "product": "CHIRPS",
        "bands": ["precipitation"],
        "unit": "mm",
        "scale_m": 5500,
        "start_date" : start_date,
        "end_date" : end_date
        }


# ----------------------------
# Compute period feature
# ----------------------------

def _reduce_mean(
    img: ee.Image, 
    band: str,
    geometry: ee.Geometry,
    scale: int
) -> ee.Dictionary:
    proj = img.select(band).projection()
    geom_in_img_crs = geometry.transform(proj, 1)
    return img.select(band).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom_in_img_crs,
        scale=scale,
        maxPixels=1e13,
        bestEffort=True,
    )



def _compute(
    prod: str,
    start: ee.Date,
    period_ic: ee.ImageCollection,
    geometry: ee.Geometry,
    scale: int,
    meta: Dict[str, Any],
) -> ee.Feature:
    n = period_ic.size()

    if prod == "CHIRPS":
        band = meta.get("band", "precipitation")
        img = period_ic.select(band).sum().rename(band)

        stats = _reduce_mean(img, band)

        return ee.Feature(None, {
            "date": start.format("YYYY-MM-dd"),
            "product": prod,
            "precipitation_mm": stats.get(band),
            "n_images": n,
            "unit": meta.get("unit", "mm"),
        })
    
    if prod in ("NDVI", "EVI"):
        band = prod 
        img = period_ic.select(band).mean().rename(band)

        stats = _reduce_mean(img, band)

        return ee.Feature(None, {
            "date": start.format("YYYY-MM-dd"),
            "product": prod,
            prod.lower(): stats.get(band),
            "n_images": n,
            "unit": meta.get("unit", prod),
            "satellite": meta.get("satellite"),
        })

    if prod == "LST":
        band = meta.get("band") or (meta.get("bands") or [None])[0]
        if not band:
            raise ValueError("LST meta must include 'band' or 'bands'")

        img = period_ic.select(band).mean().rename(band)

        unit = str(meta.get("unit", "K")).upper()
        if ("multiply" in meta) or ("add" in meta):
            m = ee.Number(meta.get("multiply", 1.0))
            a = ee.Number(meta.get("add", 0.0))
            img = img.multiply(m).add(a).subtract(273.15)
        elif unit == "K":
            img = img.subtract(273.15)

        proj = img.select(band).projection()
        geom_in_img_crs = geometry.transform(proj, 1)

        reducer = (
            ee.Reducer.mean()
            .combine(ee.Reducer.median(), sharedInputs=True)
            .combine(ee.Reducer.min(), sharedInputs=True)
            .combine(ee.Reducer.max(), sharedInputs=True)
        )

        stats = img.reduceRegion(
            reducer=reducer,
            geometry=geom_in_img_crs,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
        )

        return ee.Feature(None, {
            "date": start.format("YYYY-MM-dd"),
            "product": prod,
            "satellite": meta.get("satellite"),
            "band": band,
            "mean": stats.get(f"{band}_mean"),
            "median": stats.get(f"{band}_median"),
            "min": stats.get(f"{band}_min"),
            "max": stats.get(f"{band}_max"),
            "n_images": n,
            "unit": "°C",
        })

    if prod == "NDVI_EVI":
        img = period_ic.select(["NDVI", "EVI"]).mean().rename(["NDVI", "EVI"])

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
            "product": prod,
            "ndvi": stats.get("NDVI"),
            "evi": stats.get("EVI"),
            "n_images": n,
            "satellite": meta.get("satellite"),
        })

    raise ValueError(f"Unsupported product in _compute: {prod}")


# ----------------------------
# compute timeseries
# ----------------------------

def _dates_for_frequency(start_date: str, end_date: str, frequency: str) -> ee.List:
    freq = frequency.lower()
    unit = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}.get(freq)
    if unit is None:
        raise ValueError("frequency must be one of: daily, weekly, monthly, yearly")

    start_ee = ee.Date(start_date)
    end_ee = ee.Date(end_date)
    n = end_ee.difference(start_ee, unit).floor()
    return ee.List.sequence(0, n).map(lambda i: start_ee.advance(ee.Number(i), unit))



def _timeseries_to_df(fc: ee.FeatureCollection) -> pd.DataFrame:
    feats = fc.getInfo()["features"]
    rows = [f["properties"] for f in feats]
    return pd.DataFrame(rows)







