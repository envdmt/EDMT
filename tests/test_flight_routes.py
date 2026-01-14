import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from unittest.mock import patch, MagicMock
import duckdb

from edmt.models import get_flight_routes, _flight_polyline


INVALID_CSV_MISSING_COLS = """altitude,speed,time
100,10,1000
120,12,2000
"""

CSV_ONE_VALID_POINT = """longitude,latitude,time(millisecond)
0.0,0.0,1000
34.0,-1.0,2000
0.0,0.0,3000
"""


@pytest.fixture
def sample_metadata_df():
    return pd.DataFrame({
        "id": ["flight_1", "flight_2", "flight_3"],
        "csvLink": [
            "https://example.com/flight1.csv",
            "https://example.com/flight2.csv",
            "https://example.com/flight3.csv"
        ],
        "pilot": ["Alice", "Bob", "Charlie"]
    })


def mock_flight_polyline_success(*args, **kwargs):
    row = args[0]
    coords = [(34.0, -1.0), (34.1, -1.1), (34.2, -1.2)]
    return {
        "id": row["id"],
        "pilot": row["pilot"],
        "geometry": LineString(coords),
        "flight_distance_m": 15700.0,
        "flight_time_max_ms": 3000.0
    }


@patch("edmt.models._flight_polyline")
def test_get_flight_routes_all_fail(mock_polyline, sample_metadata_df):
    mock_polyline.return_value = None

    gdf = get_flight_routes(sample_metadata_df)

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert gdf.empty


def test_get_flight_routes_empty_input():
    df = pd.DataFrame(columns=["id", "csvLink"])
    gdf = get_flight_routes(df)

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert gdf.empty


@patch("edmt.base.ExtractCSV")
def test_flight_polyline_csv_missing_columns(mock_airdata, sample_metadata_df):
    df = pd.read_csv(pd.io.common.StringIO(INVALID_CSV_MISSING_COLS))

    mock_instance = MagicMock()
    mock_instance.df = df
    mock_airdata.return_value = mock_instance

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)

    assert result is None


@patch("edmt.base.ExtractCSV")
def test_flight_polyline_insufficient_points(mock_airdata, sample_metadata_df):
    df = pd.read_csv(pd.io.common.StringIO(CSV_ONE_VALID_POINT))

    mock_instance = MagicMock()
    mock_instance.df = df
    mock_airdata.return_value = mock_instance

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)

    assert result is None
