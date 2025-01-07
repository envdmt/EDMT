import geopandas as gpd
from shapely import make_valid

def sdf_to_gdf(sdf):
    """
    Converts a spatial dataframe (sdf) to a geodataframe (gdf).

    Steps:
    1. Creates a copy of the input spatial dataframe to avoid modifying the original.
    2. Filters out rows where the 'SHAPE' column is NaN (invalid geometries).
    3. Converts the filtered dataframe to a GeoDataFrame using the 'SHAPE' column for geometry and sets the CRS to EPSG:4326 (WGS 84).
    4. Sets the index of the GeoDataFrame to the 'objectid' column.
    5. Applies the `make_valid` function to the geometry column to correct any invalid geometries.
    6. Drops the columns 'Shape__Area', 'Shape__Length', and 'SHAPE', if they exist, to clean up the GeoDataFrame.
    7. Returns the resulting GeoDataFrame.
    """
    tmp = sdf.copy()
    tmp = tmp[~tmp['SHAPE'].isna()]
    gdf = gpd.GeoDataFrame(tmp, geometry=tmp["SHAPE"], crs=4326).set_index('OBJECTID')
    gdf['geometry'] = gdf['geometry'].apply(lambda x: make_valid(x)) # try to fix any geoemtry issues
    gdf.drop(columns=['Shape__Area', 'Shape__Length', 'SHAPE'], errors='ignore', inplace=True)
    return gdf