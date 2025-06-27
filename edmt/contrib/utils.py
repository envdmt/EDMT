import os
import sys
from dateutil import parser
import pandas as pd
import geopandas as gpd
from typing import Union
import json
from contextlib import contextmanager
from typing import Union

def clean_vars(addl_kwargs={}, **kwargs):
    for k in addl_kwargs.keys():
        print(f"Warning: {k} is a non-standard parameter. Results may be unexpected.")
        clea_ = {k: v for k, v in {**addl_kwargs, **kwargs}.items() if v is not None}
        return clea_


def normalize_column(df, col):
    # print(col)
    for k, v in pd.json_normalize(df.pop(col), sep="__").add_prefix(f"{col}__").items():
        df[k] = v.values


def dataframe_to_dict(events):
    if isinstance(events, gpd.GeoDataFrame):
        events["location"] = pd.DataFrame({"longitude": events.geometry.x, "latitude": events.geometry.y}).to_dict(
            "records"
        )
        del events["geometry"]

    if isinstance(events, pd.DataFrame):
        events = events.to_dict("records")
    return events


def clean_time_cols(df,columns = []):
    if columns:
        time_cols = [columns]
        for col in time_cols:
            if col in df.columns and not pd.api.types.is_datetime64_ns_dtype(df[col]):
                # convert x is not None to pd.isna(x) is False
                df[col] = df[col].apply(lambda x: pd.to_datetime(parser.parse(x), utc=True) if not pd.isna(x) else None)
        return df
    else:
        print("Select a column with Time format")


def format_iso_time(date_string: str) -> str:
    try:
        return pd.to_datetime(date_string).isoformat()
    except ValueError:
        raise ValueError(f"Failed to parse timestamp'{date_string}'")
    
   
# to-do : Reconfigure this section to pick same as what is being used in drones to expand_dict
def dict_columns(
        df: pd.DataFrame,
        cols: Union[str, list]) -> pd.DataFrame:
    """
    Expands columns in the DataFrame that contain lists of dictionaries (or stringified ones),
    turning each dictionary into separate flat columns.

    Args:
        df (pd.DataFrame): The input DataFrame.
        columns (list): List of column names to expand.

    Returns:
        pd.DataFrame: A new DataFrame with expanded columns.
    """
    
    dfs_to_join = []

    for col in cols:
        try:
            expanded = pd.json_normalize(df[col].explode(ignore_index=True))
            expanded.columns = [f"{col}.{subcol}" for subcol in expanded.columns]
            dfs_to_join.append(expanded)
        except Exception as e:
                print(f"Error expanding column '{col}': {e}")

    if dfs_to_join:
        expanded_df = pd.concat(dfs_to_join, axis=1)

    return df.join(expanded_df).drop(columns=cols)



def append_cols(df: pd.DataFrame, cols: Union[str, list]) -> pd.DataFrame:
    """
    Move specified column(s) to the end of the DataFrame.

    Parameters:
        df (pd.DataFrame): Input DataFrame.
        cols (str or list): Column name(s) to move to the end.

    Returns:
        pd.DataFrame: DataFrame with columns reordered.
    """
    if isinstance(cols, str):
        cols = [cols]

    remaining_cols = [col for col in df.columns if col not in cols]
    return df[remaining_cols + cols]


