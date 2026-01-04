import pytest
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from pyproj import Geod
from edmt.models import airSegment
from edmt.contrib.utils import append_cols
from shapely.geometry import LineString


def test_airSegment_basic():
    """Test basic segment generation with two points."""
    geod = Geod(ellps="WGS84")
    # Two points 1 degree apart in longitude (~111 km at equator)
    p1 = Point(0, 0)
    p2 = Point(1, 0)
    _, _, expected_dist = geod.inv(p1.x, p1.y, p2.x, p2.y)

    gdf = gpd.GeoDataFrame({
        'id': ['flight_1', 'flight_1'],
        'time(millisecond)': [1000, 2000],
        'sensor': ['X', 'X'],
        'checktime': pd.to_datetime(['2025-01-01', '2025-01-01']),
        'geometry': [p1, p2]
    }, crs="EPSG:4326")

    result = airSegment(gdf)
    result = append_cols(result, ['checktime'])

    # Assertions
    assert len(result) == 1
    assert result['id'].iloc[0] == 'flight_1'
    assert result['segment_start_time'].iloc[0] == 1000
    assert result['segment_end_time'].iloc[0] == 2000
    assert result['segment_duration_ms'].iloc[0] == 1000
    assert abs(result['segment_distance_m'].iloc[0] - expected_dist) < 1e-2
    assert result['sensor'].iloc[0] == 'X'
    assert result['checktime'].iloc[0] == pd.Timestamp('2025-01-01')
    assert result.geometry.iloc[0].equals(LineString([p1, p2]))


def test_airSegment_multiple_tracks():
    """Test handling of multiple IDs."""
    gdf = gpd.GeoDataFrame({
        'id': ['A', 'A', 'B', 'B'],
        'time(millisecond)': [1000, 2000, 1500, 2500],
        'geometry': [Point(0, 0), Point(1, 0), Point(2, 0), Point(3, 0)]
    }, crs="EPSG:4326")

    result = airSegment(gdf)
    assert len(result) == 2
    assert set(result['id']) == {'A', 'B'}


def test_airSegment_filters_zero_points():
    """Test that POINT(0 0) is filtered out."""
    gdf = gpd.GeoDataFrame({
        'id': ['test', 'test', 'test'],
        'time(millisecond)': [1000, 2000, 3000],
        'geometry': [Point(1, 1), Point(0, 0), Point(2, 2)]
    }, crs="EPSG:4326")

    result = airSegment(gdf)
    assert len(result) == 1
    assert result.geometry.iloc[0].coords[:] == [(1, 1), (2, 2)]


def test_airSegment_single_point_ignored():
    """Tracks with <2 points should produce no segments."""
    gdf = gpd.GeoDataFrame({
        'id': ['single'],
        'time(millisecond)': [1000],
        'geometry': [Point(1, 1)]
    }, crs="EPSG:4326")

    result = airSegment(gdf)
    assert len(result) == 0


def test_airSegment_empty_input():
    """Empty input should return empty GeoDataFrame."""
    gdf = gpd.GeoDataFrame(columns=['id', 'time(millisecond)', 'geometry'], crs="EPSG:4326")
    result = airSegment(gdf)
    assert len(result) == 0
    assert isinstance(result, gpd.GeoDataFrame)


def test_airSegment_preserves_metadata_from_start():
    """Metadata should come from the *starting* point of the segment."""
    gdf = gpd.GeoDataFrame({
        'id': ['demo', 'demo'],
        'time(millisecond)': [1000, 2000],
        'status': ['start', 'end'],  # Should take 'start'
        'geometry': [Point(0, 0), Point(1, 1)]
    }, crs="EPSG:4326")

    result = airSegment(gdf)
    assert result['status'].iloc[0] == 'start'