import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString
import requests
from unittest.mock import patch, MagicMock
from edmt.models import get_flight_routes, _flight_polyline
from edmt.base import AirdataCSV


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


@patch("_flight_polyline")
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


@patch("your_module._flight_polyline")
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
    with patch("your_module._flight_polyline") as mock_polyline:
        mock_polyline.side_effect = mock_flight_polyline_success
        gdf = get_flight_routes(sample_metadata_df, filter_ids=["flight_1", "flight_3"])
    
    assert len(gdf) == 2
    assert set(gdf["id"]) == {"flight_1", "flight_3"}


def test_get_flight_routes_missing_required_columns():
    df_bad = pd.DataFrame({"name": ["x"], "url": ["http://example.com"]})
    with pytest.raises(ValueError, match="Missing required columns"):
        get_flight_routes(df_bad)


@patch("_flight_polyline")
def test_get_flight_routes_custom_columns(mock_polyline, sample_metadata_df):
    # Add custom column names
    sample_metadata_df["custom_lon"] = 0  # dummy; actual data comes from CSV
    # Mock _flight_polyline to respect custom names (simplified)
    mock_polyline.side_effect = mock_flight_polyline_success

    # Just ensure it calls _flight_polyline with correct kwargs
    with patch("ThreadPoolExecutor") as mock_executor:
        mock_future = MagicMock()
        mock_future.result.return_value = mock_flight_polyline_success(sample_metadata_df.iloc[0])
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        mock_executor.return_value.__enter__.return_value.__iter__.return_value = [mock_future]

        get_flight_routes(
            sample_metadata_df,
            lon_col="custom_lon",
            lat_col="custom_lat",
            time_col="custom_time"
        )

        # Check that _flight_polyline was called with correct kwargs
        call_args = mock_polyline.call_args
        assert call_args.kwargs["lon_col"] == "custom_lon"
        assert call_args.kwargs["lat_col"] == "custom_lat"
        assert call_args.kwargs["time_col"] == "custom_time"


# Integration-style test (optional, slower): mock actual HTTP + CSV parsing
@patch("AirdataCSV")
def test_flight_polyline_integration(mock_airdata, sample_metadata_df):
    # Mock AirdataCSV to return valid DataFrame
    mock_df = pd.read_csv(pd.io.common.StringIO(VALID_CSV_CONTENT))
    mock_airdata.return_value = mock_df

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)

    assert result is not None
    assert result["id"] == "flight_1"
    assert isinstance(result["geometry"], LineString)
    assert result["flight_distance_m"] == 20000.0  # 2 segments × 10000m
    assert result["flight_time_max_ms"] == 3000.0
    assert "csvLink" not in result


# Test invalid CSV handling in _flight_polyline (via AirdataCSV returning None)
@patch("AirdataCSV")
def test_flight_polyline_csv_missing_columns(mock_airdata, sample_metadata_df):
    invalid_df = pd.read_csv(pd.io.common.StringIO(INVALID_CSV_MISSING_COLS))
    mock_airdata.return_value = invalid_df

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)
    assert result is None


@patch("AirdataCSV")
def test_flight_polyline_insufficient_points(mock_airdata, sample_metadata_df):
    df_one_point = pd.read_csv(pd.io.common.StringIO(CSV_ONE_VALID_POINT))
    mock_airdata.return_value = df_one_point

    row = sample_metadata_df.iloc[0]
    result = _flight_polyline(row)
    assert result is None


# Test the critical bug: ensure keyword arguments are passed correctly
def test_get_flight_routes_passes_kwargs_correctly(sample_metadata_df):
    """Ensure lon_col, lat_col, time_col are passed as keyword args to _flight_polyline."""
    called_kwargs = []

    def capture_kwargs(*args, **kwargs):
        called_kwargs.append(kwargs)
        return mock_flight_polyline_success(args[0])

    with patch("your_module._flight_polyline", side_effect=capture_kwargs):
        get_flight_routes(
            sample_metadata_df,
            lon_col="my_lon",
            lat_col="my_lat",
            time_col="my_time"
        )

    # Should be called once per row
    assert len(called_kwargs) == 3
    for kw in called_kwargs:
        assert kw["lon_col"] == "my_lon"
        assert kw["lat_col"] == "my_lat"
        assert kw["time_col"] == "my_time"
        # Ensure link_col is not overridden incorrectly
        assert kw.get("link_col") == "csvLink"  # default