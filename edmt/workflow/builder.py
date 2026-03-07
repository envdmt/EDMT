from __future__ import annotations

from typing import Optional, Dict, Any, Tuple, Literal
import ee
import pandas as pd
import geopandas as gpd
import shapely


# ----------------------------
# Main helpers
# ----------------------------

def ee_initialized(project: str | None = None) -> None:
    """
    Initialize Earth Engine only once.

    Notes:
    - Uses the public ee.data.is_initialized() instead of private ee.data._initialized.
    - Newer EE setups typically require a Cloud project for Initialize().
    """
    if ee.data.is_initialized():
        return

    if project:
        ee.Initialize(project=project)
    else:
        ee.Initialize()


def gdf_to_ee_geometry(
        gdf: gpd.GeoDataFrame
) -> ee.Geometry:
    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")

    if gdf.crs is None:
        raise ValueError("GeoDataFrame must have a CRS")

    gdf = gdf.to_crs(epsg=4326)
    geom = gdf.geometry.union_all()  

    geojson = shapely.geometry.mapping(geom)
    return ee.Geometry(geojson)



# --------------------------------------------------------
# Index helpers : get_satellite_collection
# --------------------------------------------------------
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



# --------------------------------------------------------
# Index Helpers : Compute_period_feature*
# --------------------------------------------------------
Frequency = Literal["daily", "weekly", "monthly", "yearly"]


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




# --------------------------------------------------------
# Index Helpers : Timeseries builder
# --------------------------------------------------------

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




# --------------------------------------------------------
# Builders
# --------------------------------------------------------

# ----------------------------
# Builders (return (ic, meta))
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
            evi = _evi_from_nir_red_blue(nir, red, blue) 
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




# --------------------------------------------------------
# Reduce stastistics helpers
# --------------------------------------------------------

def _empty(prod: str, start: ee.Date,) -> ee.Feature:
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



def _compute(prod: str,start: ee.Date,period_ic: ee.ImageCollection,geometry: ee.Geometry, scale: int,meta: Dict[str, Any],) -> ee.Feature:
    n = period_ic.size()

    def _reduce_mean(img: ee.Image, band: str) -> ee.Dictionary:
        proj = img.select(band).projection()
        geom_in_img_crs = geometry.transform(proj, 1)
        return img.select(band).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom_in_img_crs,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
        )

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



# --------------------------------------------------------
# Builder : Image Collection getter
# --------------------------------------------------------

# ----------------------------
# Helpers : Image Collection 
# ----------------------------

ReducerName = Literal["mean", "median", "min", "max", "sum"]


# ----------------------------
# Builders (return (image))
# ----------------------------
def _compute_img(
    product: str,
    start_date: str,
    end_date: str,
    ic: ee.ImageCollection,
    meta: Dict[str, Any],
    roi: Optional[ee.Geometry] = None,
    reducer: ReducerName = "mean",
) -> ee.Image:
    """
    Build a single composite ee.Image for a product using (ic, meta) from get_satellite_collection().

    - CHIRPS: reducer='sum' => total mm over period; else statistic of daily mm/day
    - NDVI/EVI: statistic over index band
    - NDVI_EVI: statistic over both bands (NDVI & EVI)
    - LST: statistic over band then convert to °C using meta (DN->K->C or K->C)
    """
    prod = product.upper()
    r = reducer.lower()

    bands = meta.get("bands") or ([meta.get("band")] if meta.get("band") else [])
    if not bands and prod != "CHIRPS":
        raise ValueError("meta must include 'bands' or 'band'")

    if roi is not None:
        first = ee.Image(ic.first())
        b0 = None
        if prod == "CHIRPS":
            b0 = meta.get("band", "precipitation")
        elif prod == "NDVI_EVI":
            b0 = "NDVI"
        else:
            b0 = prod if prod in ("NDVI", "EVI") else (meta.get("band") or bands[0])

        proj = first.select(b0).projection()
        roi = roi.transform(proj, 1)
        ic = ic.filterBounds(roi)

    if prod == "CHIRPS":
        band = meta.get("band", "precipitation")

        if r == "sum":
            img = ic.select(band).sum().rename("precipitation_mm")
            unit = "mm"
        elif r in ("mean", "median", "min", "max"):
            img = getattr(ic.select(band), r)().rename("precipitation_mm")
            unit = "mm/day"
        else:
            raise ValueError("CHIRPS reducer must be one of: sum, mean, median, min, max")

        if roi is not None:
            img = img.clip(roi)

        return img.set({
            "product": "CHIRPS",
            "start": start_date,
            "end": end_date,
            "reducer": r,
            "unit": unit,
        })

    if prod in ("NDVI", "EVI"):
        if r not in ("mean", "median", "min", "max"):
            raise ValueError("NDVI/EVI reducer must be one of: mean, median, min, max")

        band = prod
        img = getattr(ic.select(band), r)().rename(band)

        if roi is not None:
            img = img.clip(roi)

        return img.set({
            "product": prod,
            "satellite": meta.get("satellite"),
            "start": start_date,
            "end": end_date,
            "reducer": r,
            "unit": meta.get("unit", prod),
        })

    
    if prod == "NDVI_EVI":
        if r not in ("mean", "median", "min", "max"):
            raise ValueError("NDVI_EVI reducer must be one of: mean, median, min, max")

        img = getattr(ic.select(["NDVI", "EVI"]), r)().rename(["NDVI", "EVI"])

        if roi is not None:
            img = img.clip(roi)

        return img.set({
            "product": "NDVI_EVI",
            "satellite": meta.get("satellite"),
            "start": start_date,
            "end": end_date,
            "reducer": r,
            "unit": meta.get("unit", "index"),
        })

    
    if prod == "LST":
        if r not in ("mean", "median", "min", "max"):
            raise ValueError("LST reducer must be one of: mean, median, min, max")

        band = meta.get("band") or bands[0]
        img = getattr(ic.select(band), r)().rename(band)

        unit = str(meta.get("unit", "K")).upper()
        if ("multiply" in meta) or ("add" in meta):
            m = ee.Number(meta.get("multiply", 1.0))
            a = ee.Number(meta.get("add", 0.0))
            img = img.multiply(m).add(a).subtract(273.15)  
        elif unit == "K":
            img = img.subtract(273.15)                
        img = img.rename("LST_C")

        if roi is not None:
            img = img.clip(roi)

        return img.set({
            "product": "LST",
            "satellite": meta.get("satellite"),
            "band": band,
            "start": start_date,
            "end": end_date,
            "reducer": r,
            "unit": "°C",
        })

    raise ValueError(f"Unsupported product for image composite: {product}")



def _period_dates(start_date: str, end_date: str, frequency: str) -> Tuple[str, int]:
    freq = frequency.lower()
    if freq not in {"daily", "weekly", "monthly", "yearly"}:
        raise ValueError("frequency must be one of: daily, weekly, monthly, yearly")
    step_days = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}[freq]
    return freq, step_days


def _empty_img(start: ee.Date, end: ee.Date, freq: str, prod: str) -> ee.Image:
    return (
        ee.Image(0)
        .updateMask(ee.Image(0))
        .rename("empty")
        .set({
            "system:time_start": start.millis(),
            "period_start": start.format("YYYY-MM-dd"),
            "period_end": end.format("YYYY-MM-dd"),
            "frequency": freq,
            "n_images": 0,
            "product": prod,
        })
    )


def _build_period_img(
    prod: str,
    r: str,
    start: ee.Date,
    end: ee.Date,
    period_ic: ee.ImageCollection,
    meta: Dict[str, Any],
    roi: Optional[ee.Geometry],
) -> ee.Image:
    """
    Build one composite image for the period (server-side safe).
    """
    n = period_ic.size()

    if prod == "CHIRPS":
        band = meta.get("band", "precipitation")
        if r == "sum":
            img = period_ic.select(band).sum().rename("precipitation_mm").set({"unit": "mm"})
        else:
            img = getattr(period_ic.select(band), r)().rename("precipitation_mm").set({"unit": "mm/day"})

    elif prod in ("NDVI", "EVI"):
        band = prod
        img = getattr(period_ic.select(band), r)().rename(band).set({"unit": meta.get("unit", prod)})

    elif prod == "NDVI_EVI":
        img = getattr(period_ic.select(["NDVI", "EVI"]), r)().rename(["NDVI", "EVI"]).set({"unit": meta.get("unit", "index")})

    elif prod == "LST":
        band = meta.get("band") or (meta.get("bands") or [None])[0]
        img0 = getattr(period_ic.select(band), r)().rename(band)

        unit = str(meta.get("unit", "K")).upper()
        if ("multiply" in meta) or ("add" in meta):
            m = ee.Number(meta.get("multiply", 1.0))
            a = ee.Number(meta.get("add", 0.0))
            img0 = img0.multiply(m).add(a).subtract(273.15)
        elif unit == "K":
            img0 = img0.subtract(273.15)

        img = img0.rename("LST_C").set({"unit": "°C"})

    else:
        band = (meta.get("bands") or [meta.get("band")])[0]
        img = getattr(period_ic.select(band), r)().rename(band).set({"unit": meta.get("unit")})

    img = img.set({
        "system:time_start": start.millis(),
        "period_start": start.format("YYYY-MM-dd"),
        "period_end": end.format("YYYY-MM-dd"),
        "frequency": meta.get("frequency", None) or None,
        "n_images": n,
        "product": prod,
        "satellite": meta.get("satellite"),
        "reducer": r,
    })

    if roi is not None:
        img = img.clip(roi)

    return ee.Image(ee.Algorithms.If(n.gt(0), img, _empty_img(start, end, meta.get("frequency", ""), prod)))




# --------------------------------------------------------
# Raster to vector helper
# --------------------------------------------------------


def classify_image(
    image: ee.Image,
    band_name: str,
    scale: int = 1000,
    num_classes: int = 5,
    output_class_band_suffix: str = "_class"
) -> ee.Image:
    """
    Classify a single-band Earth Engine image into equal-interval classes based on its min/max values.

    The function computes global min and max of the specified band over the entire image footprint,
    divides the range into `num_classes` equal intervals, and assigns each pixel to a class (1 to N).
    The original band and the classified band are returned together.

    Parameters
    ----------
    image : ee.Image
        Input image containing at least one band. Only the specified band is used.
    band_name : str
        Name of the band to classify.
    scale : int, optional
        Nominal scale (in meters) for the reduction operation (default: 1000).
    num_classes : int, optional
        Number of equal-interval classes to create (default: 5). Must be ≥ 2.
    output_class_band_suffix : str, optional
        Suffix appended to `band_name` for the classified output band (default: "_class").

    Returns
    -------
    ee.Image
        A two-band image containing:
        - The original band (renamed to `band_name`)
        - The classified integer band (named `{band_name}{output_class_band_suffix}`)

    Notes
    -----
    - Classification uses **equal interval** bins: [min, b1), [b1, b2), ..., [bN-1, max].
    - The highest class includes the maximum value (closed upper bound).
    - If min == max (e.g., constant image), all pixels are assigned to class 1.
    - Uses `bestEffort=True` and `maxPixels=1e13` for robust global statistics.
    - Designed for visualization or simple thematic mapping—not for scientific thresholds.

    """
    if num_classes < 2:
        raise ValueError("`num_classes` must be at least 2.")

    target_band = image.select([band_name]).rename(band_name)
    stats = target_band.reduceRegion(
        reducer=ee.Reducer.minMax(),
        scale=scale,
        bestEffort=True,
        maxPixels=1e13
    )

    min_val = ee.Number(stats.get(f"{band_name}_min"))
    max_val = ee.Number(stats.get(f"{band_name}_max"))

    def _classify_normal():
        step = max_val.subtract(min_val).divide(num_classes)
        classified = ee.Image.constant(0)

        for i in range(1, num_classes + 1):
            lower = ee.Algorithms.If(
                ee.Number(i).eq(1),
                min_val,
                min_val.add(step.multiply(i - 1))
            )
            upper = min_val.add(step.multiply(i))
            in_class = target_band.gte(ee.Number(lower)).And(
                target_band.lt(upper) if i < num_classes else target_band.lte(max_val)
            )
            classified = classified.add(in_class.multiply(i))

        return classified.rename(f"{band_name}{output_class_band_suffix}").toInt()

    def _classify_constant():
        return target_band.multiply(0).add(1).rename(f"{band_name}{output_class_band_suffix}").toInt()

    classified = ee.Algorithms.If(
        min_val.eq(max_val),
        _classify_constant(),
        _classify_normal()
    )

    classified = ee.Image(classified)

    return classified.addBands(target_band)


def ee_to_polygons(
    image: ee.Image,
    scale: int = 1000,
    supported_bands: tuple[str, ...] = ("LST_C", "NDVI", "EVI", "precipitation_mm"),
) -> gpd.GeoDataFrame:
    """
    Convert an Earth Engine image to vector polygons by first classifying a supported band 
    into 5 equal-interval classes, then vectorizing regions of homogeneous class values.

    The function automatically detects which supported band is present in the image, 
    classifies it into discrete categories (1–5), and converts those categories into polygons.

    Parameters
    ----------
    image : ee.Image
        Input Earth Engine image. Must contain exactly one of the supported bands.
    scale : int, optional
        Nominal scale (in meters) for classification and vectorization (default: 1000).
    supported_bands : tuple of str, optional
        Band names that can be classified (default includes LST, NDVI, EVI, precipitation).

    Returns
    -------
    gpd.GeoDataFrame
        A GeoDataFrame in WGS84 (EPSG:4326) with:
        - `geometry`: Polygon geometries representing homogeneous classified regions
        - `class`: Integer class label (1 to 5)
        - Additional properties from the reducer (e.g., "mean" of original values)

    Raises
    ------
    ValueError
        If no supported band is found in the image, or if multiple supported bands are present.

    Notes
    -----
    - Classification uses equal-interval bins based on the global min/max of the band.
    - Vectorization uses `ee.Reducer.mean()` to preserve average original values per polygon.
    - The output CRS is always EPSG:4326 (WGS84).
    - Large or high-resolution images may exceed Earth Engine’s `maxPixels` limit—adjust `scale` if needed.
    - Designed for visualization or zonal analysis; not intended for scientific thresholding.

    Examples
    --------
    >>> lst_img = edmt.workflow.get_lst_image("2023-01-01", "2023-01-31", satellite="MODIS")
    >>> gdf = ee_image_to_polygons(lst_img, scale=1000)
    >>> print(gdf["class"].unique())  # [1, 2, 3, 4, 5]
    """
    if not isinstance(image, ee.Image):
        raise TypeError("`image` must be an ee.Image instance.")

    bands = image.bandNames().getInfo()

    available_supported = [b for b in supported_bands if b in bands]

    if not available_supported:
        raise ValueError(
            f"No supported band found for classification. "
            f"Image bands: {bands}. Supported: {supported_bands}"
        )
    
    if len(available_supported) > 1:
        raise ValueError(
            f"Multiple supported bands detected: {available_supported}. "
            f"Please ensure the image contains only one band to classify."
        )

    target_band = available_supported[0]

    classified_image = classify_image(
        image=image,
        band_name=target_band,
        scale=scale,
        num_classes=5,
        output_class_band_suffix="_class"
    )

    vectors = classified_image.reduceToVectors(
        geometry=image.geometry(),
        scale=scale,
        geometryType="polygon",
        reducer=ee.Reducer.mean(),
        labelProperty="class",
        maxPixels=1e13,
        bestEffort=True
    )

    features = vectors.getInfo()
    if not features or "features" not in features or not features["features"]:
        raise RuntimeError("Vectorization returned no features. Check image validity and scale.")

    gdf = gpd.GeoDataFrame.from_features(features["features"], crs="EPSG:4326")

    return gdf


def ee_to_points(
        image: ee.Image, 
        scale: int=30, 
        num_pixels: int = 5000
    ) -> gpd.GeoDataFrame:
    """
    Sample pixels as points and return GeoDataFrame.
    """

    fc = image.sample(
        scale=scale,
        numPixels=num_pixels,
        geometries=True
    )

    geojson = fc.getInfo()
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])
    gdf = gdf.set_crs("EPSG:4326")

    return gdf







