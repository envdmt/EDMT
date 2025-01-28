import os
import requests
import geopandas as gpd
import pandas as pd
from typing import Union
# from google.colab import files
# import json

def config():
    # uploaded = files.upload()
    # config_file_name = list(uploaded.keys())[0]
    # with open(config_file_name, mode='r') as file:
    #     config = json.load(file)
    # return config
    n="Still testing"
    return print(n)

def read_url(url_path: str, local_file: str = "downloaded_file") -> Union[gpd.GeoDataFrame, pd.DataFrame]:
    """
    Reads a file from a URL and returns it as a GeoDataFrame or DataFrame.

    Args:
        url_path (str): The URL of the file to download.
        local_file (str): The name of the local file to save the downloaded content. Defaults to "downloaded_file".

    Returns:
        Union[gpd.GeoDataFrame, pd.DataFrame]: A GeoDataFrame if the file contains spatial data, otherwise a DataFrame.
    """
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
        with requests.get(url_path, stream=True) as response:
            response.raise_for_status()
            with open(local_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
        
        # gdf = gpd.read_file(local_file, engine="pyogrio")
        # return gdf
        try:
            gdf = gpd.read_file(local_file, engine="pyogrio")
            return gdf
        except:
            df = pd.read_csv(local_file)
            return df
    
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error fetching file from URL: {e}")
    
    except OSError as e:
        raise OSError(f"Error saving or accessing the local file: {e}")
    
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)


