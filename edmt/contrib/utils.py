from dateutil import parser
import pandas as pd

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
    


def dict_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Expands columns in the DataFrame that contain lists of dictionaries (or stringified ones),
    turning each dictionary into separate flat columns.

    Args:
        df (pd.DataFrame): The input DataFrame.
        columns (list): List of column names to expand.

    Returns:
        pd.DataFrame: A new DataFrame with expanded columns.
    """
    df = df.copy()

    for col in columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame")
        expanded = df[col].apply(pd.Series).stack().apply(pd.Series)
        expanded = expanded.reset_index(level=1, drop=True)
        expanded.index = df.index 
        expanded.columns = [f"{col}.{subcol}" for subcol in expanded.columns]

    return pd.concat([df.drop(col, axis=1), expanded], axis=1)


