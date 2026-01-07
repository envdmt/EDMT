import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
from unittest.mock import patch, MagicMock
from edmt.models import get_flight_routes, _flight_polyline
from concurrent.futures import ThreadPoolExecutor, as_completed

# Sample valid CSV content
VALID_CSV_CONTENT = """longitude,latitude,time(millisecond)
34.0, -1.0, 1000
34.1, -1.1, 2000
34.2, -1.2, 3000
"""

# CSV missing required columns
INVALID_CSV_MISSING_COLS = """altitude,speed,time
100,10,1000
120,12,2000
"""

# CSV with only one valid point (after filtering zeros)
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


# Mock successful CSV download and processing
def mock_flight_polyline_success(row, **kwargs):
    # Simulate successful return from _flight_polyline
    coords = [(34.0 + i*0.1, -1.0 - i*0.1) for i in range(3)]
    line = LineString(coords)
    return {
        "id": row["id"],
        "pilot": row["pilot"],
        "geometry": line,
        "flight_distance_m": 15700.0,
        "flight_time_max_ms": 3000.0
    }


def mock_flight_polyline_none(row, **kwargs):
    return None


@patch("edmt.models._flight_polyline")
def test_get_flight_routes_success(mock_polyline, sample_metadata_df):
    mock_polyline.side_effect = mock_flight_polyline_success

    gdf = get_flight_routes(sample_metadata_df, max_workers=2)

    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 3
    assert "geometry" in gdf.columns
    assert gdf.crs == "EPSG:4326"
    assert list(gdf["id"]) == ["flight_1", "flight_2", "flight_3"]
    assert "csvLink" not in gdf.columns


@patch("edmt.models._flight_polyline")
def test_get_flight_routes_partial_success(mock_polyline, sample_metadata_df):
    # Simulate one failure
    def side_effect(row, **kwargs):
        if row["id"] == "flight_2":
            return None
        return mock_flight_polyline_success(row, **kwargs)

    mock_polyline.side_effect = side_effect

    gdf = get_flight_routes(sample_metadata_df)

    assert len(gdf) == 2
    assert set(gdf["id"]) == {"flight_1", "flight_3"}

@patch("edmt.models._flight_polyline")
def test_get_flight_routes_all_fail(mock_polyline, sample_metadata_df):
    mock_polyline.return_value = None
    gdf = get_flight_routes(sample_metadata_df)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 0


def test_get_flight_routes_empty_input():
    df = pd.DataFrame(columns=["id", "csvLink"])
    gdf = get_flight_routes(df)
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert len(gdf) == 0


def test_get_flight_routes_filter_ids(sample_metadata_df):
    with patch("edmt.models._flight_polyline") as mock_polyline:
        mock_polyline.side_effect = mock_flight_polyline_success
        gdf = get_flight_routes(sample_metadata_df, filter_ids=["flight_1", "flight_3"])
    
    assert len(gdf) == 2
    assert set(gdf["id"]) == {"flight_1", "flight_3"}


# Test invalid CSV handling in _flight_polyline (via AirdataCSV returning None)
@patch("edmt.base.AirdataCSV")
def test_flight_polyline_csv_missing_columns(mock_airdata, sample_metadata_df):
    invalid_df = pd.read_csv(pd.io.common.StringIO(INVALID_CSV_MISSING_COLS))
    mock_airdata.return_value = invalid_df

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)
    assert result is None


@patch("edmt.base.AirdataCSV")
def test_flight_polyline_insufficient_points(mock_airdata, sample_metadata_df):
    df_one_point = pd.read_csv(pd.io.common.StringIO(CSV_ONE_VALID_POINT))
    mock_airdata.return_value = df_one_point

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)
    assert result is None

