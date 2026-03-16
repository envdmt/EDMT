import pytest
import pandas as pd
import geopandas as gpd
import json
import requests
import http.client
from unittest.mock import patch, MagicMock
from shapely.geometry import LineString

# Adjust import paths as needed for your project structure
from edmt.models import (
    Airdata,
    _flight_polyline,
    get_flight_routes,
)
from edmt.base import ExtractCSV


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def mock_authenticate():
    with patch("edmt.models.Airdata.authenticate"):
        yield
        
@pytest.fixture
def authenticated_airdata():
    return Airdata(api_key="fake", skip_auth=True)


@pytest.fixture
def unauthenticated_airdata():
    """Return an unauthenticated Airdata instance."""
    ad = Airdata(api_key="fake", skip_auth=True)
    ad.authenticated = False
    return ad


@pytest.fixture
def sample_flights_df():
    return pd.DataFrame({
        "id": ["flight1", "flight2"],
        "csvLink": [
            "https://example.com/flight1.csv",
            "https://example.com/flight2.csv"
        ]
    })


# =============================================================================
# Test: get_drones
# =============================================================================

@patch("http.client.HTTPSConnection")
def test_get_drones_success(mock_conn_class, authenticated_airdata):
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps([{"drone_id": "D1", "model": "Phantom"}]).encode()
    mock_conn.getresponse.return_value = mock_response
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_drones()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.iloc[0]["drone_id"] == "D1"
    assert df.iloc[0]["model"] == "Phantom"


@patch("http.client.HTTPSConnection")
def test_get_drones_empty_response(mock_conn_class, authenticated_airdata):
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps([]).encode()
    mock_conn.getresponse.return_value = mock_response
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_drones()
    assert df.empty


def test_get_drones_unauthenticated(unauthenticated_airdata):
    df = unauthenticated_airdata.get_drones()
    assert df.empty


@patch("http.client.HTTPSConnection")
def test_get_drones_http_error(mock_conn_class, authenticated_airdata):
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 500
    mock_response.read.return_value = b'{"error": "Server error"}'
    mock_conn.getresponse.return_value = mock_response
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_drones()
    assert df.empty


# =============================================================================
# Test: get_pilots
# =============================================================================

@patch("http.client.HTTPSConnection")
def test_get_pilots_success(mock_conn_class, authenticated_airdata):
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps([
        {"pilot_id": "P1", "name": "Alice"},
        {"pilot_id": "P2", "name": "Bob"}
    ]).encode()
    mock_conn.getresponse.return_value = mock_response
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_pilots()
    assert len(df) == 2
    assert list(df["pilot_id"]) == ["P1", "P2"]
    assert list(df["name"]) == ["Alice", "Bob"]


def test_get_pilots_unauthenticated(unauthenticated_airdata):
    df = unauthenticated_airdata.get_pilots()
    assert df.empty


# =============================================================================
# Test: get_flights
# =============================================================================

@patch("http.client.HTTPSConnection")
def test_get_flights_success(mock_conn_class, authenticated_airdata):
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    flight_data = {"data": [{"id": "F1", "time": "2023-01-01T12:00:00Z", "drone_id": "D1"}]}
    mock_response.read.return_value = json.dumps(flight_data).encode()
    mock_conn.getresponse.return_value = mock_response
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_flights(limit=1, max_pages=1)
    assert len(df) == 1
    assert df.iloc[0]["id"] == "F1"
    assert "checktime" in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["checktime"])


@patch("http.client.HTTPSConnection")
def test_get_flights_no_data(mock_conn_class, authenticated_airdata):
    mock_conn = MagicMock()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps({"data": []}).encode()
    mock_conn.getresponse.return_value = mock_response
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_flights()
    assert df.empty


def test_get_flights_unauthenticated(unauthenticated_airdata):
    df = unauthenticated_airdata.get_flights()
    assert df.empty


@patch("http.client.HTTPSConnection")
def test_get_flights_pagination(mock_conn_class, authenticated_airdata):
    page1 = {"data": [{"id": "f1", "time": "2023-01-01T00:00:00Z"}]}
    page2 = {"data": []}

    mock_conn = MagicMock()
    mock_conn.getresponse.side_effect = [
        MagicMock(status=200, read=lambda: json.dumps(page1).encode()),
        MagicMock(status=200, read=lambda: json.dumps(page2).encode()),
    ]
    mock_conn_class.return_value = mock_conn

    df = authenticated_airdata.get_flights(limit=1, max_pages=2)
    assert len(df) == 1
    assert "checktime" in df.columns


def test_get_flights_invalid_location(authenticated_airdata):
    with pytest.raises(ValueError, match="Location must be a list of exactly two numbers"):
        authenticated_airdata.get_flights(location=[1.0])
    with pytest.raises(ValueError, match="Location must be a list of exactly two numbers"):
        authenticated_airdata.get_flights(location=[1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="Location must be a list of exactly two numbers"):
        authenticated_airdata.get_flights(location=["a", "b"])


# =============================================================================
# Test: Flight Route Processing
# =============================================================================

def test_flight_polyline_invalid_url():
    row = pd.Series({"id": "bad", "csvLink": "not_a_url"})
    assert _flight_polyline(row) is None


def test_flight_polyline_insufficient_points(monkeypatch):
    def mock_extract(*args, **kwargs):
        return pd.DataFrame({
            "longitude": [0.0],
            "latitude": [0.0],
            "time(millisecond)": [1000]
        })
    monkeypatch.setattr("edmt.base.ExtractCSV", mock_extract)
    row = pd.Series({"id": "short", "csvLink": "http://fake.csv"})
    assert _flight_polyline(row) is None


def test_get_flight_routes_success(monkeypatch, sample_flights_df):
    def mock_polyline(row, **kwargs):
        return {
            "id": row["id"],
            "geometry": LineString([(0, 0), (1, 1)]),
            "airline_distance_m": 100.0,
            "airline_time": 2000,
            "pilot": "test"
        }
    monkeypatch.setattr("edmt.models._flight_polyline", mock_polyline)

    gdf = get_flight_routes(sample_flights_df, max_workers=1)
    assert isinstance(gdf, gpd.GeoDataFrame)


def test_get_flight_routes_empty_input():
    df = pd.DataFrame()
    with pytest.raises(ValueError, match="Missing required columns"):
        get_flight_routes(df)


def test_get_flight_routes_filtered(sample_flights_df):
    gdf = get_flight_routes(sample_flights_df)
    assert isinstance(gdf, gpd.GeoDataFrame)

