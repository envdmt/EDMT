import os
import ee
import geopandas as gpd
import shapely

def initialize_gee():
    """
    Initialize Google Earth Engine with explicit project support.
    """

    EE_PROJECT = os.getenv("EE_PROJECT")  # REQUIRED
    EE_ACCOUNT = os.getenv("EE_ACCOUNT")
    EE_PRIVATE_KEY_DATA = os.getenv("EE_PRIVATE_KEY_DATA")

    if not EE_PROJECT:
        raise RuntimeError(
            "EE_PROJECT environment variable is required "
            "(Google Cloud project ID with Earth Engine enabled)"
        )

    try:
        if EE_ACCOUNT and EE_PRIVATE_KEY_DATA:
            credentials = ee.ServiceAccountCredentials(
                EE_ACCOUNT,
                key_data=EE_PRIVATE_KEY_DATA
            )
            ee.Initialize(credentials=credentials, project=EE_PROJECT)
        else:
            ee.Initialize(project=EE_PROJECT)

    except ee.EEException:
        ee.Authenticate()
        ee.Initialize(project=EE_PROJECT)


def geodf_to_ee_geometry(
    gdf: gpd.GeoDataFrame
) -> ee.Geometry:
    """
    Convert a GeoDataFrame polygon/multipolygon to ee.Geometry.

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Must contain Polygon or MultiPolygon geometries

    Returns
    -------
    ee.Geometry
    """

    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")

    if gdf.crs is None:
        raise ValueError("GeoDataFrame must have a CRS")

    gdf = gdf.to_crs(epsg=4326)

    geom = gdf.union_all()
    geojson = shapely.geometry.mapping(geom)

    return ee.Geometry(geojson)
