import pytest
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import uuid
from unittest.mock import patch

# Import your module
from edmt.conversion import (
    convert_time,
    convert_speed,
    convert_distance,
    get_utm_epsg
)

# --------------------------
# Test: convert_time
# --------------------------
def test_convert_time():
    assert convert_time(60, "seconds", "minutes") == 1.0
    assert convert_time(1, "hour", "seconds") == 3600.0
    assert convert_time(1000, "ms", "s") == 1.0
    assert convert_time(1, "microsecond", "s") == 0.0
    assert convert_time(2629800, "seconds", "month") == 1.0

def test_convert_time_invalid_unit():
    with pytest.raises(ValueError, match="Invalid 'unit_from'"):
        convert_time(10, "blargh", "seconds")
    with pytest.raises(ValueError, match="Invalid 'unit_to'"):
        convert_time(10, "seconds", "xyz")

def test_convert_time_negative_value():
    with pytest.raises(ValueError, match="'time_value' must be a non-negative number"):
        convert_time(-5, "s", "min")


# --------------------------
# Test: convert_speed
# --------------------------
def test_convert_speed():
    assert convert_speed(10, "m/s", "km/h") == 36.0
    assert convert_speed(1, "km/h", "mph") == pytest.approx(0.621, rel=1e-3)
    assert convert_speed(1, "knot", "km/h") == pytest.approx(1.852, rel=1e-3)

def test_convert_speed_invalid_unit():
    with pytest.raises(ValueError):
        convert_speed(10, "furlongs/fortnight", "km/h")


# --------------------------
# Test: convert_distance
# --------------------------
def test_convert_distance_metric():
    assert convert_distance(1000, "m", "km") == 1.0
    assert convert_distance(1, "km", "m") == 1000.0
    assert convert_distance(10, "cm", "mm") == 100.0

def test_convert_distance_imperial():
    assert convert_distance(1, "mi", "ft") == pytest.approx(5280.0, rel=1e-3)
    assert convert_distance(12, "in", "ft") == 1.0

def test_convert_distance_mixed():
    assert convert_distance(1, "mi", "m") == pytest.approx(1609.344, rel=1e-3)
    assert convert_distance(100, "m", "yd") == pytest.approx(109.361, rel=1e-3)

def test_convert_distance_invalid_unit():
    with pytest.raises(ValueError, match="Invalid 'from_type'"):
        convert_distance(10, "lightyears", "km")



# --------------------------
# Test: get_utm_epsg
# --------------------------
def test_get_utm_epsg():
    assert get_utm_epsg(0) == "32631"   # Zone 31N
    assert get_utm_epsg(-179) == "32701"  # Zone 1S
    assert get_utm_epsg(179) == "32660"   # Zone 60N

def test_get_utm_epsg_none():
    with pytest.raises(KeyError, match="Select column with longitude values"):
        get_utm_epsg()







