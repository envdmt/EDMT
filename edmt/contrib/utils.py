import aiohttp
import pandas as pd
from io import StringIO
from typing import Union
from dateutil import parser
from typing import Optional, List
from tqdm.asyncio import tqdm_asyncio
import nest_asyncio
nest_asyncio.apply()



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


async def fetch_csv(session: aiohttp.ClientSession, row, log_errors: bool = True) -> Optional[pd.DataFrame]:
    """
    Asynchronously fetches a CSV file from a URL and enriches its rows with metadata.

    This function retrieves a CSV from the URL specified in `row.csvLink`, parses it into a
    pandas DataFrame, and then adds metadata columns (taken from the input `row`) to every
    row of the CSV data. If the request fails or parsing errors occur, the function returns
    `None` and optionally logs the error.

    Parameters
    ----------
    session : aiohttp.ClientSession
        An active aiohttp session used to make the HTTP GET request.
    row : pandas.Series or namedtuple-like object
        An object with at least two attributes:
        - `csvLink`: the URL to the CSV file (str)
        - `id`: a unique identifier for logging/error reporting (any)
        Other attributes will be duplicated as metadata columns.
    log_errors : bool, optional
        If True (default), errors will be printed to stdout with the associated row ID.

    Returns
    -------
    pd.DataFrame or None
        A DataFrame combining the original CSV data and repeated metadata from `row`.
        Returns None if an exception occurs during fetch or parsing.
    """
    try:
        async with session.get(row.csvLink, timeout=aiohttp.ClientTimeout(total=100)) as r:
            r.raise_for_status()  
            text = await r.text() 

        csv_data = pd.read_csv(StringIO(text))

        meta = pd.DataFrame([row._asdict()] * len(csv_data), index=csv_data.index)

        return pd.concat([meta, csv_data], axis=1)

    except Exception as e:
        if log_errors:
            print(f"[Error] id={row.id}: {e}")
        return None


async def load_all_csvs(df: pd.DataFrame, log_errors: bool = True, max_conn: int = 32) -> List[pd.DataFrame]:
    """
    Asynchronously downloads and processes multiple CSV files defined in a DataFrame.

    This function concurrently fetches CSV files using URLs from the `csvLink` column of
    the input DataFrame `df`. Each CSV is enriched with its corresponding metadata row.
    Results are collected in a list of DataFrames. Failed fetches are silently skipped
    (unless `log_errors=True`).

    Uses `tqdm_asyncio` to display a real-time progress bar during execution.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing at least:
        - `csvLink`: URL to each CSV file (str)
        - `id`: unique identifier for error reporting (any)
        Other columns are treated as metadata and replicated into the fetched CSV data.
    log_errors : bool, optional
        Whether to print error messages for failed downloads (default: True).
    max_conn : int, optional
        Maximum number of concurrent TCP connections (default: 32). Passed to aiohttp's
        TCPConnector to limit parallelism and avoid overwhelming the server or OS.

    Returns
    -------
    List[pd.DataFrame]
        A list of successfully fetched and enriched DataFrames. Order does not necessarily
        match input `df` due to asynchronous completion order.

    Notes
    -----
    - Requires `nest_asyncio.apply()` if running inside a Jupyter notebook or nested event loop.
    - Uses `tqdm_asyncio.as_completed()` for progress tracking without blocking concurrency.
    - Memory usage scales with the number and size of CSVs—use cautiously on large datasets.
    """
    connector = aiohttp.TCPConnector(limit=max_conn, ttl_dns_cache=300)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_csv(session, row, log_errors) for row in df.itertuples(index=False)]

        results = []
        for coro in tqdm_asyncio.as_completed(tasks, total=len(tasks), desc="Processing Flights"):
            res = await coro
            if res is not None:
                results.append(res)

    return results

