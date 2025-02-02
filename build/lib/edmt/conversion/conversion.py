import os
import uuid
import pandas as pd
import geopandas as gpd
# from osgeo import ogr
import requests
from shapely import make_valid

from edmt.contrib import clean_vars


def sdf_to_gdf(sdf, crs=None,shape=None):
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
    # Validate input DataFrame
    if not isinstance(sdf, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame.")
    if sdf.empty:
        raise ValueError("DataFrame is empty. Cannot generate UUIDs for an empty DataFrame.")

    # clean vars
    params = clean_vars(
        shape = shape,
        geometry = "geometry",
        columns = ["Shape__Area", "Shape__Length", "SHAPE"],
        crs=crs
    )
    assert params.get("geometry") is None
    print("Geometry column is present and valid")

    tmp = sdf.copy()
    tmp = tmp[~tmp[params.get("shape")].isna()]

    if crs:
        crs=params.get("crs")
    else:
        crs=4326

    gdf = gpd.GeoDataFrame(
        tmp, 
        geometry=tmp[params.get("shape")], 
        crs=crs
        )
    gdf['geometry'] = gdf[params.get("geometry")].apply(lambda x: make_valid(x)) # Validate geometries
    gdf.drop(columns=params.get("columns"), errors='ignore', inplace=True)
    print("COnverted Spatial DataFrame to GeoDataFrame")
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
       
def get_utm_epsg(longitude=None):
    if longitude is None:
       print("KeyError : Select column with longitude values")
    else:
        zone_number = int((longitude + 180) / 6) + 1
        hemisphere = '6' if longitude >= 0 else '7'  # 6 for Northern, 7 for Southern Hemisphere
        return f"32{hemisphere}{zone_number:02d}"
    
"""
Issue Installing GDAL, To check a better way to convert or a way to install osgeo
"""
# def kml_to_geojson(file_path=None,url=None):
#     if file_path and url is None:
#         print("file path and url invalid.")
#     else:
#         driver = ogr.GetDriverByName('KML')
#         dataSource = driver.Open(file_path or url, 0)

#         if dataSource:
#             layer = dataSource.GetLayer()
#             geojson_driver = ogr.GetDriverByName('GeoJSON')
#             output_folder = f"Drone - {file_path}"

#             if os.path.exists(output_folder):
#                 os.remove(output_folder)
#             geojson_ds = geojson_driver.CreateDataSource(output_folder)
#             geojson_ds.CopyLayer(layer, layer.GetName())
#             geojson_ds.Destroy()
#             dataSource.Destroy()
#             print(f"Successuflly Converted KML to GeoJSON and saved to {output_folder}")


def read_file_from_url(url_path: str, local_file: str = "downloaded_file"):
    """
    Reads a file from a given URL, downloads it locally, and loads it as a GeoDataFrame.

    Parameters:
    ----------
    url_path : str
        The URL of the file to download.
    local_file : str, optional
        The name of the local file to save the downloaded content (default: "downloaded_file").

    Returns:
    -------
    gpd.GeoDataFrame
        A GeoDataFrame loaded from the downloaded file.

    Raises:
    ------
    ValueError:
        If `url_path` is None or empty.
    requests.exceptions.RequestException:
        If there is an issue during the HTTP request.
    OSError:
        If there is an issue writing the local file.
    """
    if not url_path:
        raise ValueError("The 'url_path' parameter cannot be None or empty.")
    
    try:
        # Download the file from the given URL
        with requests.get(url_path, stream=True) as response:
            response.raise_for_status()
            with open(local_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        
        # Load the file into a GeoDataFrame
        gdf = gpd.read_file(local_file, engine="pyogrio")
        return gdf
    
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching file from URL: {e}")
    
    except OSError as e:
        raise OSError(f"Error saving or accessing the local file: {e}")
    
    finally:
        # Optional: Clean up the local file after reading if needed
        if os.path.exists(local_file):
            os.remove(local_file)