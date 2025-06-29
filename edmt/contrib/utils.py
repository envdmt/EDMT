import os
import sys
from dateutil import parser
import pandas as pd
import geopandas as gpd
from contextlib import contextmanager
from typing import Union, List

def clean_vars(addl_kwargs={}, **kwargs):
    for k in addl_kwargs.keys():
        print(f"Warning: {k} is a non-standard parameter. Results may be unexpected.")
        clea_ = {k: v for k, v in {**addl_kwargs, **kwargs}.items() if v is not None}
        return clea_


def normalize_column(df, col):
    # print(col)
    for k, v in pd.json_normalize(df.pop(col), sep="__").add_prefix(f"{col}__").items():
        df[k] = v.values


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
    

def norm_exp(df: pd.DataFrame, cols : Union[str, list]) -> pd.DataFrame:
    """
    Normalizes specified columns containing list of dicts,
    expands them into separate rows if needed,
    and appends new columns to the original dataframe with prefixing.

    Parameters:
    - df: Original pandas DataFrame
    - cols: str or list of str, names of columns to normalize

    Returns:
    - Modified DataFrame with normalized and expanded data
    """
    if isinstance(cols, str):
        cols = [cols]

    result_df = df.copy()
    for col in cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame.")

        s = df[col]
        normalized = s.apply(lambda x: pd.json_normalize(x) if isinstance(x, list) and x else pd.DataFrame())
        def add_prefix(df_sub, prefix):
            df_sub.cols = [f"{prefix}_{subcol}" for subcol in df_sub.columns]
            return df_sub

        normalized = normalized.map(lambda df_sub: add_prefix(df_sub, col))
        normalized_stacked = (
            pd.concat(normalized.tolist(), keys=df.index)
            .reset_index(level=1, drop=True)
            .rename_axis('original_index')
            .reset_index()
        )
        result_df = result_df.drop(columns=[col], errors='ignore')

    return result_df.merge(
            normalized_stacked,
            left_index=True,
            right_on='original_index',
            how='left'
        ).drop(columns=['original_index'])


def append_cols(df: pd.DataFrame, cols: Union[str, list]):
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


def norm_exp(df: pd.DataFrame,
    cols: Union[str, list]
) -> pd.DataFrame:
    """
    Normalizes specified columns containing list of dicts,
    expands them into separate rows if needed,
    and appends new columns to the original dataframe with prefixing.

    Parameters:
    - df: Original pandas DataFrame
    - columns: str or list of str, names of columns to normalize

    Returns:
    - Modified DataFrame with normalized and expanded data
    """
    if isinstance(cols, str):
        cols = [cols]

    result_df = df.copy()
    for col in cols:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame.")

        s = df[col]
        normalized = s.apply(lambda x: pd.json_normalize(x) if isinstance(x, list) and x else pd.DataFrame())
        def add_prefix(df_sub, prefix):
            df_sub.columns = [f"{prefix}_{subcol}" for subcol in df_sub.columns]
            return df_sub

        normalized = normalized.map(lambda df_sub: add_prefix(df_sub, col))
        normalized_stacked = (
            pd.concat(normalized.tolist(), keys=df.index)
            .reset_index(level=1, drop=True)
            .rename_axis('original_index')
            .reset_index()
        )
        result_df = result_df.drop(columns=[col], errors='ignore')

    return result_df.merge(
            normalized_stacked,
            left_index=True,
            right_on='original_index',
            how='left'
        ).drop(columns=['original_index'])