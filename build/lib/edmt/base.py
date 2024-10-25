# import necessary modules
import pandas as pd
import geopandas as gpd
from shapely.validation import make_valid
import uuid

pd.set_option('display.max_columns', None)

########################################################################################################3#
##  Convert sdf to gdf
def sdf_to_gdf(sdf,original_crs=None,target_crs=4326,**addl_kwargs):
    """
    Converts spatial dataframe to geodataframe whilst ensuring;
    1) Coordinates are in EPSG:4326; 
    2) Drops unnecessary column
    3) Fix any geometry issues
    4) Sets geometry column to a geometry datatype 
    """
    # Copy the GeoDataFrame to avoid modifying the original
    tmp = sdf.copy()
    # Select rows with values and leave out Null rows in SHAPE column 
    tmp = tmp[~tmp['SHAPE'].isna()]
    # Convert file to Geodataframe
    gdf = gpd.GeoDataFrame(tmp, geometry=tmp['SHAPE'], crs=f"EPSG:{original_crs}").set_index('OBJECTID')
    # Fix any geometry issues
    gdf['geometry'] = gdf['geometry'].astype(object).apply(lambda x: make_valid(x))
    # Drop Unnecessary columns
    gdf.drop(columns=['Shape___Area','Shape__Length','SHAPE'], errors='ignore', inplace=True)
    # Transform to the target CRS
    gdf = gdf.to_crs(epsg=target_crs)
    # Set geomtery column to geometry
    gdf = gdf.set_geometry('geometry')
    # Return geodataframe
    return gdf
    
###############################################################################################################
## Convert gdf to sdf

def gdf_to_sdf(gdf, original_crs=4326, target_crs=None):
    """
    Converts Geodataframe to Spatial dataframe
    1) Convert crs to 32736 (UTM Zone 36S)
    2) 
    """
    # If a target CRS is provided, transform the GeoDataFrame to it
    if target_crs:
        gdf = gdf.to_crs(epsg=target_crs)
    # Copy the GeoDataFrame to avoid modifying the original
    tmp = gdf.copy()
    # Rename 'geometry' column back to 'SHAPE' for sdf compatibility
    tmp['SHAPE'] = tmp['geometry']
    # Drop the 'geometry' column as it will be replaced by 'SHAPE'
    tmp.drop(columns=['geometry'], inplace=True)
    # Convert the GeoDataFrame back to a Spatial DataFrame    # Optionally, if required, set the CRS of the sdf to the original CRS
    sdf = tmp.crs = f"EPSG:{original_crs}"
    
    # Return sdf
    return sdf
    
## Function to generate UUID
def generate_uuid( df,**addl_kwargs):
    """
    Returns a string of uuids.
    """
    df['id'] = [str(uuid.uuid4()).lower() for _ in range(len(df))]
    return df.set_index('id')


