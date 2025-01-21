sorters_ = ["datasets","fillers"]


# use sklaern to add datasets and sorters for filling Nan Values by impute
import geopandas as gpd
import pandas as pd
import sklearn

def sorters(df=None):
    print("Its working")
    return df

def datasets():#geom=None):

    # df = pd.read_csv() # use this for plotting and remove geometry columns

    # if geom:
    #     df = gpd.GeoDataFrame(
    #         df, geom='geonetry'
    #     ) # convert the dataset to a geodataframe
    # else:
    #     # add a section for sklearn datasets

    # # fetch_california_housing
    """
    link : https://scikit-learn.org/stable/modules/generated/sklearn.datasets.fetch_california_housing.html#sklearn.datasets.fetch_california_housing
    """
    df = sklearn.datasets.fetch_california_housing(data_home=None, download_if_missing=True, return_X_y=False, as_frame=False, n_retries=3, delay=1.0)
    return df

def filler(df,column=None,method=None):
    # remove nan values by filling using Sklearn impute
    if column:
        print(f"{column} filled {method} filler")
    return df
