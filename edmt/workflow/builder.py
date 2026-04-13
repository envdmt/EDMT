from __future__ import annotations

from typing import Optional, Dict, Any, Literal
import ee
import pandas as pd
import geopandas as gpd
import shapely

Frequency = Literal["daily", "weekly", "monthly", "yearly"]
ReducerName = Literal["mean", "median", "sum", "min", "max"]
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


def _freq_unit(frequency: str) -> str:
    freq_map = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",

        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
    }

    try:
        return freq_map[frequency.lower()]
    except KeyError:
        raise ValueError(
            f"Invalid frequency '{frequency}'. Use: daily, weekly, monthly, yearly"
        )


def _advance_end(start: ee.Date, frequency: str) -> ee.Date:
    unit = _freq_unit(frequency)
    return start.advance(1, unit)


def _make_dates(start: ee.Date, end: ee.Date, frequency: str) -> ee.List:
    unit = _freq_unit(frequency)

    n = end.difference(start, unit).ceil()

    return ee.List.sequence(0, n.subtract(1)).map(
        lambda i: start.advance(ee.Number(i), unit)
    )


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
    }

    if prod == "LST":
        base.update({"mean": None, "median": None, "min": None, "max": None})

    elif prod == "CHIRPS":
        base["precipitation_mm"] = None

    elif prod in ("NDVI", "EVI"):
        base[prod.lower()] = None

    if meta and "unit" in meta:
        base["unit"] = meta["unit"]

    return ee.Feature(None, base)


def _reduce_stats(img: ee.Image, geometry: ee.Geometry, scale: int) -> ee.Dictionary:
    geom = geometry.transform(img.projection(), 1)

    return img.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.minMax(), sharedInputs=True
        ),
        geometry=geom,
        scale=scale,
        maxPixels=1e13,
        tileScale=16,
        bestEffort=True,
    )

# ----------------------------
# 2 : Builders (return (ic, meta))
# ----------------------------

# Master registry
_PRODUCT_REGISTRY = {
    "LST": "lst",
    "NDVI": "vegetation",
    "EVI": "vegetation",
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
            "collection": "COPERNICUS/S2_SR_HARMONIZED",
            "bands": {"blue": "B2", "red": "B4", "nir": "B8"},
            "scale": 10000.0,
            "mask": "SENTINEL2",
            "scale_m": 30,
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


def _ndvi_from_nir_red(nir: ee.Image, red: ee.Image) -> ee.Image:
    return nir.subtract(red).divide(nir.add(red)).rename("NDVI")


def _evi_from_nir_red_blue(nir: ee.Image, red: ee.Image, blue: ee.Image) -> ee.Image:
    nir  = nir.clamp(0, 1)
    red  = red.clamp(0, 1)
    blue = blue.clamp(0, 1)

    numerator = nir.subtract(red).multiply(2.5)
    denominator = (
        nir.add(red.multiply(6))
           .subtract(blue.multiply(7.5))
           .add(1)
    )

    denominator = denominator.where(denominator.abs().lt(1e-6), 1e-6)
    evi = numerator.divide(denominator)
    evi = evi.clamp(-1, 1)

    return evi.rename("EVI")


def _mask_s2(img):
    scl = img.select("SCL")
    mask = (
        scl.neq(3)
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )

    return img.updateMask(mask)


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
    product = product.upper()
    sat = _norm_sat(satellite)

    cfg = _SAT_CONFIG["VEG"].get(sat)
    if not cfg:
        raise ValueError(f"Unsupported vegetation satellite: {satellite}")

    ic = ee.ImageCollection(cfg["collection"]).filterDate(start_date, end_date)

    if product not in ("NDVI", "EVI"):
        raise ValueError(f"Unsupported vegetation product: {product}")

    # MODIS 
    if cfg.get("direct"):

        band_map = {
            "NDVI": cfg["bands"]["ndvi"],
            "EVI": cfg["bands"]["evi"],
        }

        src_band = band_map[product]

        def _proc(img):
            return (
                img.select(src_band)
                   .multiply(cfg["scale"])
                   .rename(product)
                   .copyProperties(img, ["system:time_start"])
            )

        return ic.map(_proc), {
            "bands": [product],
            "scale_m": cfg["scale_m"],
            "satellite": sat,
            "product": product,
            "direct": True
        }

    # Derived NDVI / EVI
    def _proc(img):
        if cfg["mask"] == "SENTINEL2":
            img = _mask_s2(img)
        else:
            img = _mask_landsat(img)

        # Reflectance extraction
        if sat.startswith("LANDSAT"):
            blue = _sr(img, cfg["bands"]["blue"])
            red  = _sr(img, cfg["bands"]["red"])
            nir  = _sr(img, cfg["bands"]["nir"])
        else:
            scale = cfg.get("scale", 10000.0)

            blue = img.select(cfg["bands"]["blue"]).divide(scale).clamp(0, 1)
            red  = img.select(cfg["bands"]["red"]).divide(scale).clamp(0, 1)
            nir  = img.select(cfg["bands"]["nir"]).divide(scale).clamp(0, 1)

        # Compute index
        if product == "NDVI":
            out = _ndvi_from_nir_red(nir, red).rename("NDVI")

        elif product == "EVI":
            out = _evi_from_nir_red_blue(nir, red, blue).rename("EVI")

        return out.copyProperties(img, ["system:time_start"])

    return ic.map(_proc), {
        "bands": [product],
        "scale_m": cfg["scale_m"],
        "satellite": sat,
        "product": product,
        "direct": False
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
def _compute_lst(start, period_ic, geometry, scale, meta, n=None):
    band = "LST"
    satellite = meta.get("satellite").upper()
    img = period_ic.select(band).mean().subtract(273.15)

    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=scale,
        crs=img.projection(),
        maxPixels=1e13,
        tileScale=16,
        bestEffort=True,
    )


    return ee.Feature(None, {
        "date": start.format("YYYY-MM-dd"),
        "product": band,
        "satellite": satellite,
        "mean": stats.get("LST"),
        "unit": "°C",
    })


# NDVI/EVI
def _compute_veg(prod, start, period_ic, geometry, scale, meta):
    band = prod
    satellite = meta.get("satellite").upper()
    img = period_ic.select(band).reduce(ee.Reducer.mean()).rename(band)

    stats = img.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=scale,
        crs=img.select(band).projection(),
        maxPixels=1e13,
        tileScale=16, 
        bestEffort=True,
    )

    return ee.Feature(None, {
        "date": start.format("YYYY-MM-dd"),
        "product": prod,
        prod.lower(): stats.get(band),
        "satellite": satellite,
    })


# CHIRPS
def _compute_chirps(start, period_ic, geometry, scale, meta):
    band = (meta.get("bands") or ["precipitation"])[0]
    img = period_ic.select(band).sum().rename(band)

    stats = img.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=geometry,
        scale=scale,
        crs=img.select(band).projection(),
        maxPixels=1e13,
        tileScale=16, 
        bestEffort=True,
    )

    return ee.Feature(None, {
        "date": start.format("YYYY-MM-dd"),
        "product": "CHIRPS",
        "precipitation_mm": stats.get(band),
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

    func = _COMPUTE_REGISTRY.get(prod)

    if not func:
        raise ValueError(f"Unsupported product in _compute: {prod}")

    if prod in ("NDVI", "EVI"):
        return func(prod, start, period_ic, geometry, scale, meta)

    return func(start, period_ic, geometry, scale, meta)









# ----------------------------
# Composite Build
# ----------------------------

def _lst_composite(start, end, period_ic, meta, reducer):
    band = meta["bands"][0]
    img = getattr(period_ic.select(band), reducer)()

    m = ee.Number(meta.get("multiply", 1.0))
    a = ee.Number(meta.get("add", 0.0))
    img = img.multiply(m).add(a)

    if str(meta.get("unit", "K")).upper() == "K":
        img = img.subtract(273.15)

    return img.rename("LST_C").set({
        "period_start": start.format("YYYY-MM-dd"),
        "period_end": end.format("YYYY-MM-dd"),
        "product": "LST",
        "reducer": reducer,
        "unit": "°C",
        "satellite": meta["satellite"],
    })


# NDVI/EVI
def _veg_composite(start, end, period_ic, meta, reducer):
    band = meta["bands"][0]
    img = getattr(period_ic.select(band), reducer)()

    return img.rename(band).set({
        "period_start": start.format("YYYY-MM-dd"),
        "period_end": end.format("YYYY-MM-dd"),
        "product": meta["product"],
        "reducer": reducer,
        "unit": "index",
        "satellite": meta["satellite"],
    })


# CHIRPS
def _chirps_composite(start, end, period_ic, meta, reducer):

    band = meta["bands"][0]
    n = period_ic.size()

    if reducer == "sum":
        img = period_ic.select(band).sum()
        unit = "mm"
    else:
        img = getattr(period_ic.select(band), reducer)()
        unit = "mm/day"

    return img.rename("precipitation_mm").set({
        "period_start": start.format("YYYY-MM-dd"),
        "period_end": end.format("YYYY-MM-dd"),
        "product": "CHIRPS",
        "reducer": reducer,
        "unit": unit,
        "satellite": meta["satellite"],
    })



_COMPOSITE_BUILDERS = {
    "LST": _lst_composite,
    "NDVI": _veg_composite,
    "EVI": _veg_composite,
    "CHIRPS": _chirps_composite,
}


def _composite_image(product, start, end, period_ic, meta, reducer="mean"):

    product = _norm_sat(product)

    if product not in _COMPOSITE_BUILDERS:
        raise ValueError(f"Unsupported product: {product}")

    builder = _COMPOSITE_BUILDERS[product]

    return builder(
        start=start,
        end=end,
        period_ic=period_ic,
        meta=meta,
        reducer=reducer,
    )











# ----------------------------
# Collection Build
# ----------------------------

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

    n = period_ic.size()

    img = _composite_image(
        product=prod,
        start=start,
        end=end,
        period_ic=period_ic,
        meta=meta,
        reducer=r,
    )

    img = img.set({
        "system:time_start": start.millis(),
        "period_start": start.format("YYYY-MM-dd"),
        "period_end": end.format("YYYY-MM-dd"),
        "month" : ee.String(start.format("MMMM")),
        "frequency": meta.get("frequency"),
        "n_images": n,
        "product": prod,
        "satellite": meta.get("satellite"),
        "reducer": r,
    })

    if roi is not None:
        img = img.clip(roi)

    return ee.Image(
        ee.Algorithms.If(
            n.gt(0),
            img,
            _empty_img(start, end, meta.get("frequency", ""), prod)
        )
    )

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







