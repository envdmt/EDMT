import pandas as pd
import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon
from edmt.conversion import sdf_to_gdf




# Test with valid input and extra columns to drop
def test_sdf_to_gdf_valid_input():
    df = pd.DataFrame({
        'name': ['A', 'B'],
        'SHAPE': [Point(1, 2), Point(2, 3)],
        'Shape__Area': [10, 20],
        'Shape__Length': [5, 6]
    })
    gdf = sdf_to_gdf(df, crs="EPSG:4326")
    
    # Check that the output is a GeoDataFrame
    assert isinstance(gdf, gpd.GeoDataFrame)
    
    # Check that the CRS is set correctly
    assert gdf.crs == "EPSG:4326"
    
    # Check that extra columns are dropped
    for col in ['Shape__Area', 'Shape__Length', 'SHAPE']:
        assert col not in gdf.columns
        
    # Check that geometries are valid and are instances of shapely geometries
    for geom in gdf.geometry:
        assert geom.is_valid
        assert hasattr(geom, "geom_type")

# Test that CRS remains None when not provided
def test_sdf_to_gdf_no_crs():
    df = pd.DataFrame({
        'name': ['A', 'B'],
        'SHAPE': [Point(1, 2), Point(2, 3)]
    })
    gdf = sdf_to_gdf(df)
    # If no CRS is provided, gdf.crs should be None or not set
    assert gdf.crs is None

# Test filtering of rows with NaN geometries
def test_sdf_to_gdf_nan_geometries():
    df = pd.DataFrame({
        'name': ['A', 'B', 'C'],
        'SHAPE': [Point(1, 2), None, Point(3, 4)]
    })
    gdf = sdf_to_gdf(df)
    # Should drop the row with None geometry, so length should be 2
    assert len(gdf) == 2

# Test behavior with an invalid geometry that needs to be fixed.
def test_sdf_to_gdf_invalid_geometry():
    # Create a self-intersecting polygon (commonly considered invalid)
    invalid_poly = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    df = pd.DataFrame({
        'name': ['A'],
        'SHAPE': [invalid_poly]
    })
    gdf = sdf_to_gdf(df)
    # After applying make_valid (our dummy version uses buffer(0) if invalid),
    # the geometry should be valid.
    for geom in gdf.geometry:
        assert geom.is_valid

if __name__ == '__main__':
    pytest.main()
