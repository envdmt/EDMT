# use sklaern to add datasets and sorters for filling Nan Values by impute
import geopandas as gpd
import pandas as pd

def sorters(df=None):
    print("Its working")
    return df

def datasets(geom=None):

    df = pd.read_csv() # use this for plotting and remove geometry columns

    if geom:
        df = gpd.GeoDataFrame(
            df, geom='geonetry'
        ) # convert the dataset to a geodataframe
    else:
        return df

def filler(df,column=None,method=None):
    # remove nan values by filling using Sklearn impute
    if column:
        print(f"{column} filled {method} filler")
    return df
