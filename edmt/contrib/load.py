import os
import requests
import geopandas as gpd
from google.colab import files
import json

def config():
    uploaded = files.upload()
    config_file_name = list(uploaded.keys())[0]
    with open(config_file_name, mode='r') as file:
        config = json.load(file)
    return config

def read_url(url_path: str, local_file: str = "downloaded_file") -> gpd.GeoDataFrame:
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


