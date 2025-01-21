import uuid
import pandas as pd

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
                return df  # Return without modifying the index

    print("No UUID-like column found. Generating 'uuid' column in the DataFrame.")

    # Add or update 'uuid' column with UUIDs
    if 'uuid' not in df.columns:
        df['uuid'] = [str(uuid.uuid4()).lower() for _ in range(len(df))]
    else:
        df['uuid'] = df['uuid'].apply(lambda x: x if pd.notnull(x) else str(uuid.uuid4()).lower())

    # Set 'uuid' as index if requested
    if index:
        df = df.set_index('uuid').reset_index()

    return df