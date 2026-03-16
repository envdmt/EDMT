import pytest
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon
import uuid
from edmt.conversion import (
    sdf_to_gdf,
    generate_uuid,
    generate_cmap,
    get_utm_epsg,
    convert_time,
    convert_speed,
    convert_distance,
    convert_temperature
)

from edmt.conversion.conversion import (
    _is_valid_uuid, _find_uuid_like_column,format_temperature
)

# --- Helper Fixtures ---

@pytest.fixture
def sample_sdf():
    return pd.DataFrame({
        "SHAPE": [Point(0, 0), Point(1, 1)],
        "name": ["A", "B"],
        "Shape__Area": [1.0, 2.0],
        "Shape__Length": [1.0, 2.0]
    })

@pytest.fixture
def sample_df():
    return pd.DataFrame({"name": ["Alice", "Bob"]})

# --- UUID Tests ---

def test_is_valid_uuid():
    assert _is_valid_uuid("f47ac10b-58cc-4372-a567-0e02b2c3d479") is True
    assert _is_valid_uuid("invalid") is False
    assert _is_valid_uuid(None) is False
    assert _is_valid_uuid("") is False

def test_find_uuid_like_column():
    df = pd.DataFrame(columns=["id", "user_uuid", "value"])
    assert _find_uuid_like_column(df) == "user_uuid"
    df2 = pd.DataFrame(columns=["ID", "UUID_FIELD", "val"])
    assert _find_uuid_like_column(df2, ("uuid",)) == "UUID_FIELD"
    df3 = pd.DataFrame(columns=["id", "name"])
    assert _find_uuid_like_column(df3) is None

def test_generate_uuid_new(sample_df):
    df_out = generate_uuid(sample_df)
    assert "uuid" in df_out.columns
    assert len(df_out) == 2
    assert all(_is_valid_uuid(u) for u in df_out["uuid"])

def test_generate_uuid_repair():
    df = pd.DataFrame({
        "uuid": ["invalid", "f47ac10b-58cc-4372-a567-0e02b2c3d479"],
        "val": [1, 2]
    })
    df_out = generate_uuid(df)
    assert _is_valid_uuid(df_out.loc[0, "uuid"])
    assert df_out.loc[1, "uuid"] == "f47ac10b-58cc-4372-a567-0e02b2c3d479"

def test_generate_uuid_force(sample_df):
    df_with = generate_uuid(sample_df)
    uuid1 = df_with["uuid"].iloc[0]
    df_forced = generate_uuid(df_with, force=True)
    uuid2 = df_forced["uuid"].iloc[0]
    assert uuid1 != uuid2  # Should be regenerated

def test_generate_uuid_index_position(sample_df):
    df_front = generate_uuid(sample_df, index=True)
    assert df_front.columns[0] == "uuid"
    df_back = generate_uuid(sample_df, index=False)
    assert df_back.columns[-1] == "uuid"

# --- GeoDataFrame Conversion ---

def test_sdf_to_gdf(sample_sdf):
    gdf = sdf_to_gdf(sample_sdf, crs="EPSG:4326")
    assert isinstance(gdf, gpd.GeoDataFrame)
    assert gdf.crs.to_string() == "EPSG:4326"
    assert "SHAPE" not in gdf.columns
    assert "geometry" in gdf.columns

def test_sdf_to_gdf_empty():
    empty_df = pd.DataFrame()
    with pytest.raises(ValueError, match="empty"):
        sdf_to_gdf(empty_df)

def test_sdf_to_gdf_invalid_input():
    with pytest.raises(ValueError, match="DataFrame"):
        sdf_to_gdf("not a df")

# --- UTM EPSG ---

def test_get_utm_epsg():
    assert get_utm_epsg(0) == "32631"   # Zone 31N
    assert get_utm_epsg(-180) == "32701"  # Zone 1S
    assert get_utm_epsg(179) == "32660"   # Zone 60N
    with pytest.raises(KeyError):
        get_utm_epsg()

# --- Colormap Generation ---

def test_generate_cmap():
    data = [1, 2, 3, 4, 5]
    labels, colors = generate_cmap(data, 3)
    assert len(labels) == 3
    assert len(colors) == 3
    assert all(c.startswith("#") for c in colors)
    assert "1.00 -" in labels[0]

def test_generate_cmap_constant():
    data = [5, 5, 5]
    labels, colors = generate_cmap(data, 5)
    assert len(labels) == 1
    assert labels[0] == "5.00"

def test_generate_cmap_empty():
    with pytest.raises(ValueError):
        generate_cmap([], 2)

# --- Time Conversion ---

def test_convert_time():
    assert convert_time(60, "seconds", "minutes") == 1.0
    assert convert_time(1, "hours", "seconds") == 3600.0
    assert convert_time(1000, "ms", "seconds") == 1.0
    assert convert_time(1, "day", "hours") == 24.0

def test_convert_time_invalid():
    with pytest.raises(ValueError):
        convert_time(-1, "s", "min")
    with pytest.raises(ValueError):
        convert_time(1, "xyz", "s")

# --- Speed Conversion ---

def test_convert_speed():
    assert convert_speed(10, "m/s", "km/h") == 36.0
    assert convert_speed(1, "km/h", "mph") == pytest.approx(0.621, rel=1e-3)

def test_convert_speed_invalid():
    with pytest.raises(ValueError):
        convert_speed(10, "m/s", "lightyear/century")

# --- Distance Conversion ---

def test_convert_distance():
    assert convert_distance(1000, "m", "km") == 1.0
    assert convert_distance(1, "mi", "m") == pytest.approx(1609.344)
    assert convert_distance(10, "cm", "mm") == 100.0

def test_convert_distance_invalid():
    with pytest.raises(ValueError):
        convert_distance(1, "parsecs", "km")

# --- Temperature Conversion ---

def test_convert_temperature():
    assert convert_temperature(0, "C", "K") == 273.15
    assert convert_temperature(32, "F", "C") == 0.0
    assert convert_temperature(273.15, "K", "C") == 0.0

def test_convert_temperature_invalid():
    with pytest.raises(ValueError):
        convert_temperature(-300, "K", "C")  # Below 0 K
    with pytest.raises(ValueError):
        convert_temperature(0, "Rankine", "C")

def test_format_temperature():
    assert format_temperature(25.5, "C") == "25.5 °C"
    assert format_temperature(298.65, "K", symbol=False) == "298.65 K"
    assert format_temperature(77, "F", decimals=0) == "77 °F"

# --- Edge Cases ---

def test_generate_uuid_empty_df():
    empty = pd.DataFrame()
    with pytest.raises(ValueError):
        generate_uuid(empty)

def test_convert_time_zero():
    assert convert_time(0, "hours", "seconds") == 0.0
