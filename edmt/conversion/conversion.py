conversion_ = [
    "sdf_to_gdf","generate_uuid","kml_to_geojson","get_utm_epsg"
    ]


import os
import uuid
import pandas as pd
import geopandas as gpd
from osgeo import ogr
from shapely import make_valid

def sdf_to_gdf(sdf):
    """
    Converts a spatial dataframe (sdf) to a geodataframe (gdf).

    Steps:
    1. Creates a copy of the input spatial dataframe to avoid modifying the original.
    2. Filters out rows where the 'SHAPE' column is NaN (invalid geometries).
    3. Converts the filtered dataframe to a GeoDataFrame using the 'SHAPE' column for geometry and sets the CRS to EPSG:4326 (WGS 84).
    4. Sets the index of the GeoDataFrame to the 'objectid' column. (removed this)
    5. Applies the `make_valid` function to the geometry column to correct any invalid geometries.
    6. Drops the columns 'Shape__Area', 'Shape__Length', and 'SHAPE', if they exist, to clean up the GeoDataFrame.
    7. Returns the resulting GeoDataFrame.
    """
    tmp = sdf.copy()
    tmp = tmp[~tmp['SHAPE'].isna()]
    gdf = gpd.GeoDataFrame(tmp, geometry=tmp["SHAPE"], crs=4326)
    gdf['geometry'] = gdf['geometry'].apply(lambda x: make_valid(x)) # try to fix any geoemtry issues
    gdf.drop(columns=['Shape__Area', 'Shape__Length', 'SHAPE'], errors='ignore', inplace=True)
    return gdf

def generate_uuid(df, index=False):
    """
    Adds a unique 'uuid' column with UUIDs to the DataFrame if no existing UUID-like column is found.
    Does not generate new UUIDs if UUIDs are already assigned in a 'uuid' column.

    Args:
        df (pd.DataFrame): The DataFrame to which UUIDs will be added.
        index (bool): If True, sets 'uuid' as the index. Otherwise, 'uuid' remains a column.

    Returns:
        pd.DataFrame: DataFrame with a 'uuid' column added if no UUID-like column exists.
    Raises:
        ValueError: If 'df' is not a DataFrame or if it's empty.
    """

    # Validate input DataFrame
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("DataFrame is empty. Cannot generate UUIDs for an empty DataFrame.")

    # Define UUID pattern
    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'

    # Check for existing UUID-like columns
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) and df[col].str.match(uuid_pattern).all():
            print(f"Column '{col}' contains UUID-like values.")
            if index:
                return df.set_index(col).reset_index()
            else:
                return df  #

    print("No UUID-like column found. Generating 'uuid' column in the DataFrame.")

    if 'uuid' not in df.columns:
        df['uuid'] = [str(uuid.uuid4()).lower() for _ in range(len(df))]
    else:
        df['uuid'] = df['uuid'].apply(lambda x: x if pd.notnull(x) else str(uuid.uuid4()).lower())

    if index:
        df = df.set_index('uuid').reset_index()

    return df

def kml_to_geojson(file_path=None,url=None):
    if file_path and url is None:
        print("file path and url invalid.")
    else:
        driver = ogr.GetDriverByName('KML')
        dataSource = driver.Open(file_path or url, 0)

        if dataSource:
            layer = dataSource.GetLayer()
            geojson_driver = ogr.GetDriverByName('GeoJSON')
            output_folder = f"Drone - {file_path}"

            if os.path.exists(output_folder):
                os.remove(output_folder)
            geojson_ds = geojson_driver.CreateDataSource(output_folder)
            geojson_ds.CopyLayer(layer, layer.GetName())
            geojson_ds.Destroy()
            dataSource.Destroy()
            print(f"Successuflly Converted KML to GeoJSON and saved to {output_folder}")
       
def get_utm_epsg(longitude=None):
    if longitude is None:
       print("KeyError : Select column with longitude values")
    else:
        zone_number = int((longitude + 180) / 6) + 1
        hemisphere = '6' if longitude >= 0 else '7'  # 6 for Northern, 7 for Southern Hemisphere
        return f"32{hemisphere}{zone_number:02d}"