import geopandas as gpd
from shapely import make_valid

def sdf_to_gdf(sdf, crs=4326):
    """
    Converts a spatial dataframe (sdf) to a geodataframe (gdf) with a user-defined CRS.

    Parameters:
    - sdf: Spatial DataFrame to convert.
    - crs: Coordinate Reference System (default is EPSG:4326).

    Steps:
    1. Creates a copy of the input spatial dataframe to avoid modifying the original.
    2. Filters out rows where the 'SHAPE' column is NaN (invalid geometries).
    3. Converts the filtered dataframe to a GeoDataFrame using the 'SHAPE' column for geometry and sets the CRS.
    4. Applies the `make_valid` function to the geometry column to correct any invalid geometries.
    5. Drops the columns 'Shape__Area', 'Shape__Length', and 'SHAPE', if they exist, to clean up the GeoDataFrame.
    6. Returns the resulting GeoDataFrame.
    """
    tmp = sdf.copy()
    tmp = tmp[~tmp['SHAPE'].isna()]
    
    # Allow user to define CRS
    gdf = gpd.GeoDataFrame(tmp, geometry=tmp["SHAPE"], crs=crs)
    
    # Validate geometries
    gdf['geometry'] = gdf['geometry'].apply(lambda x: make_valid(x))
    
    # Drop unnecessary columns
    gdf.drop(columns=['Shape__Area', 'Shape__Length', 'SHAPE'], errors='ignore', inplace=True)
    
    return gdf
