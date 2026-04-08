from __future__ import annotations

from typing import Optional, Dict, Any, Tuple, Literal
import ee
import pandas as pd
import geopandas as gpd
import shapely

Frequency = Literal["daily", "weekly", "monthly", "yearly"]

# ----------------------------
# 1 : Main helpers
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


# Index helpers 

def _norm_sat(x: Optional[str]) -> str:
    return (x or "").strip().upper().replace("-", "_").replace(" ", "_")


def _copy_time(img: ee.Image) -> ee.Image:
    return img.copyProperties(img, ["system:time_start"])


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


def _dates_for_frequency(start_date: str, end_date: str, frequency: str) -> ee.List:
    freq = frequency.lower()
    unit = {"daily": "day", "weekly": "week", "monthly": "month", "yearly": "year"}.get(freq)
    if unit is None:
        raise ValueError("frequency must be one of: daily, weekly, monthly, yearly")

    start_ee = ee.Date(start_date)
    end_ee = ee.Date(end_date)
    n = end_ee.difference(start_ee, unit).floor()
    return ee.List.sequence(0, n).map(lambda i: start_ee.advance(ee.Number(i), unit))


def _ndvi_from_nir_red(nir: ee.Image, red: ee.Image) -> ee.Image:
    return nir.subtract(red).divide(nir.add(red)).rename("NDVI")


def _evi_from_nir_red_blue(nir: ee.Image, red: ee.Image, blue: ee.Image) -> ee.Image:
    return nir.subtract(red).multiply(2.5).divide(
        nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)
    ).rename("EVI")


def _apply_lst_scale(img, mult, add, band):
    return (
        img.select(band)
           .multiply(mult)
           .add(add)
           .rename("LST")
           .copyProperties(img, ["system:time_start"])
    )


def _timeseries_to_df(fc: ee.FeatureCollection) -> pd.DataFrame:
    feats = fc.getInfo()["features"]
    rows = [f["properties"] for f in feats]
    return pd.DataFrame(rows)


def _empty(prod: str, start: ee.Date, meta: Dict[str, Any] = None) -> ee.Feature:
    prod = prod.upper()

    base = {
        "date": start.format("YYYY-MM-dd"),
        "product": prod,
        "n_images": 0,
    }

    if prod == "LST":
        base.update({"mean": None, "median": None, "min": None, "max": None})

    elif prod == "CHIRPS":
        base["precipitation_mm"] = None

    elif prod == "NDVI_EVI":
        base.update({"ndvi": None, "evi": None})

    elif prod in ("NDVI", "EVI"):
        base[prod.lower()] = None

    # Optional: attach unit if available
    if meta and "unit" in meta:
        base["unit"] = meta["unit"]

    return ee.Feature(None, base)

# ----------------------------
# 2 : Builders (return (ic, meta))
# ----------------------------

# Master registry

_PRODUCT_REGISTRY = {
    "LST": "lst",
    "NDVI": "vegetation",
    "EVI": "vegetation",
    "NDVI_EVI": "vegetation",
    "CHIRPS": "chirps",
}

# Satellite configs


_SAT_CONFIG = {
    "LST": {
        "LANDSAT8": {
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "band": "ST_B10",
            "scale_m": 30,
            "scale": {"type": "landsat"}
        },
        "LANDSAT9": {
            "collection": "LANDSAT/LC09/C02/T1_L2",
            "band": "ST_B10",
            "scale_m": 30,
            "scale": {"type": "landsat"}
        },
        "MODIS": {
            "collection": "MODIS/061/MOD11A1",
            "band": "LST_Day_1km",
            "scale_m": 1000,
            "scale": {"type": "linear", "mult": 0.02, "add": 0.0}
        },
        "GCOM": {
            "collection": "JAXA/GCOM-C/L3/LAND/LST/V3",
            "band": "LST_AVE",
            "scale_m": 5000,
            "scale": {"type": "linear", "mult": 0.02, "add": 0.0} 
        }
    },

    "VEG": {
        "SENTINEL2": {
            "collection": "COPERNICUS/S2_HARMONIZED",
            "bands": {"blue": "B2", "red": "B4", "nir": "B8"},
            "scale": 10000.0,
            "mask": "S2",
            "scale_m": 10,
        },
        "LANDSAT8": {
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "bands": {"blue": "SR_B2", "red": "SR_B4", "nir": "SR_B5"},
            "mask": "LANDSAT",
            "scale_m": 30,
        },
        "LANDSAT9": {
            "collection": "LANDSAT/LC09/C02/T1_L2",
            "bands": {"blue": "SR_B2", "red": "SR_B4", "nir": "SR_B5"},
            "mask": "LANDSAT",
            "scale_m": 30,
        },
        "MODIS": {
            "collection": "MODIS/061/MOD13Q1",
            "bands": {"ndvi": "NDVI", "evi": "EVI"},
            "scale": 0.0001,
            "scale_m": 250,
            "direct": True,
        },
    }
}


# ----------------------------------
# Core helpers (reused everywhere)
#-----------------------------------

def _mask_s2(img):
    qa = img.select("QA60")
    return img.updateMask(
        qa.bitwiseAnd(1 << 10).eq(0)
        .And(qa.bitwiseAnd(1 << 11).eq(0))
    )

def _mask_landsat(img):
    qa = img.select("QA_PIXEL")
    return img.updateMask(
        qa.bitwiseAnd(1 << 3).eq(0)
        .And(qa.bitwiseAnd(1 << 4).eq(0))
    )

def _sr(img, band):
    return img.select(band).multiply(0.0000275).add(-0.2)

def _scale_lst(img, band, scale_cfg):
    if scale_cfg["type"] == "landsat":
        return (
            img.select(band)
               .multiply(0.00341802)
               .add(149.0)
               .rename("LST")
               .copyProperties(img, ["system:time_start"])
        )

    elif scale_cfg["type"] == "linear":
        return (
            img.select(band)
               .multiply(scale_cfg.get("mult", 1))
               .add(scale_cfg.get("add", 0))
               .rename("LST")
               .copyProperties(img, ["system:time_start"])
        )

    else:
        raise ValueError("Unknown scaling type")


# -------------
# LST pipeline
# -------------


def _build_lst(satellite, start_date, end_date):
    sat = _norm_sat(satellite)
    cfg = _SAT_CONFIG["LST"].get(sat)

    if not cfg:
        raise ValueError(f"Unsupported LST satellite: {satellite}")

    ic = ee.ImageCollection(cfg["collection"]).filterDate(start_date, end_date)

    def _proc(img):
        return _scale_lst(img, cfg["band"], cfg["scale"])

    return ic.map(_proc), {
        "bands": ["LST"],
        "scale_m": cfg["scale_m"],
        "unit": "K",
    }



# ---------------------
# Vegetation pipeline
#----------------------

def _build_vegetation(product, satellite, start_date, end_date):
    sat = _norm_sat(satellite)
    cfg = _SAT_CONFIG["VEG"].get(sat)

    if not cfg:
        raise ValueError(f"Unsupported vegetation satellite: {satellite}")

    ic = ee.ImageCollection(cfg["collection"]).filterDate(start_date, end_date)

    # MODIS shortcut
    if cfg.get("direct"):
        bands = []
        if product in ("NDVI", "NDVI_EVI"):
            bands.append(cfg["bands"]["ndvi"])
        if product in ("EVI", "NDVI_EVI"):
            bands.append(cfg["bands"]["evi"])

        def _proc(img):
            return (
                img.select(bands)
                   .multiply(cfg["scale"])
                   .rename(bands)
                   .copyProperties(img, ["system:time_start"])
            )

        return ic.map(_proc), {"bands": bands, "scale_m": cfg["scale_m"]}

    def _proc(img):
        # mask
        if cfg["mask"] == "S2":
            img = _mask_s2(img)
        else:
            img = _mask_landsat(img)

        # bands
        if sat.startswith("LANDSAT"):
            blue = _sr(img, cfg["bands"]["blue"])
            red  = _sr(img, cfg["bands"]["red"])
            nir  = _sr(img, cfg["bands"]["nir"])
        else:
            scale = cfg.get("scale", 10000.0)
            blue = img.select(cfg["bands"]["blue"]).divide(scale)
            red  = img.select(cfg["bands"]["red"]).divide(scale)
            nir  = img.select(cfg["bands"]["nir"]).divide(scale)

        outputs = []

        if product in ("NDVI", "NDVI_EVI"):
            outputs.append(_ndvi_from_nir_red(nir, red).rename("NDVI"))

        if product in ("EVI", "NDVI_EVI"):
            outputs.append(_evi_from_nir_red_blue(nir, red, blue).rename("EVI"))

        out = outputs[0] if len(outputs) == 1 else outputs[0].addBands(outputs[1])

        return out.copyProperties(img, ["system:time_start"])

    return ic.map(_proc), {
        "bands": ["NDVI", "EVI"] if product == "NDVI_EVI" else [product],
        "scale_m": cfg["scale_m"],
    }


# ----------------
# CHIRPS pipeline
# ----------------

def _build_chirps(start_date, end_date):
    ic = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(start_date, end_date)
        .select(["precipitation"])
        .map(lambda img: img.rename("precipitation")
             .copyProperties(img, ["system:time_start"]))
    )

    return ic, {"bands": ["precipitation"], "scale_m": 5500}



# -----------------
# 3 : Computation
# -----------------

# LST

def _compute_lst(start, period_ic, geometry, scale, meta, n):
    band = "LST"
    img = period_ic.select(band).mean().subtract(273.15)

    reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.median(), sharedInputs=True)
    )

    stats = img.reduceRegion(
        reducer=reducer,
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        tileScale=16, 
        bestEffort=True,
    )

    return ee.Feature(None, {
        "date": start.format("YYYY-MM-dd"),
        "product": "LST",
        "satellite": meta.get("satellite"),
        "mean": stats.get("LST_mean"),
        "median": stats.get("LST_median"),
        "n_images": n,
        "unit": "°C",
    })


# NDVI/EVI

def _compute_veg(prod, start, period_ic, geometry, scale, meta, n):
    band = prod
    img = period_ic.select(band).mean()

    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        tileScale=16, 
        bestEffort=True,
    )

    return ee.Feature(None, {
        "date": start.format("YYYY-MM-dd"),
        "product": prod,
        prod.lower(): stats.get(band),
        "n_images": n,
        "satellite": meta.get("satellite"),
    })



# CHIRPS
def _compute_chirps(start, period_ic, geometry, scale, meta, n):
    band = (meta.get("bands") or ["precipitation"])[0]
    img = period_ic.select(band).sum().rename(band)

    stats = img.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13,
        tileScale=16, 
        bestEffort=True,
    )

    return ee.Feature(None, {
        "date": start.format("YYYY-MM-dd"),
        "product": "CHIRPS",
        "precipitation_mm": stats.get(band),
        "n_images": n,
        "unit": meta.get("unit", "mm"),
    })



# Compute Registry

_COMPUTE_REGISTRY = {
    "CHIRPS": _compute_chirps,
    "NDVI": _compute_veg,
    "EVI": _compute_veg,
    "LST": _compute_lst,
}

# ------------------
# Unified Compute
# -------------------

def _compute(
    prod: str,
    start: ee.Date,
    period_ic: ee.ImageCollection,
    geometry: ee.Geometry,
    scale: int,
    meta: Dict[str, Any],
) -> ee.Feature:

    n = period_ic.size()
    prod = prod.upper()

    func = _COMPUTE_REGISTRY.get(prod)

    if not func:
        raise ValueError(f"Unsupported product in _compute: {prod}")

    if prod in ("NDVI", "EVI"):
        return func(prod, start, period_ic, geometry, scale, meta, n)

    return func(start, period_ic, geometry, scale, meta, n)















# --------------------------------------------------------
# Builder : Image Collection getter
# --------------------------------------------------------

# ----------------------------
# Helpers : Image Collection 
# ----------------------------

ReducerName = Literal["mean", "median", "min", "max"]


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
        elif r in ReducerName:
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
        if r not in ReducerName:
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







