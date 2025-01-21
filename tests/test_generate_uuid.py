import edmt
import geopandas as gpd
import pytest
from unittest.mock import patch


@pytest.fixture
def mock_geojson():
    """
    Create a mock GeoDataFrame to simulate loading a GeoJSON file.
    This avoids relying on external URLs or slow network operations.
    """
    return gpd.GeoDataFrame(
        {
            "name": ["Location 1", "Location 2"], 
            "geometry": [None, None],
        }
    )


def test_generate_uuid(mock_geojson):
    """
    Test the 'generate_uuid' function from the 'edmt.conversion' module.

    Steps:
    1. Mock the 'read_file' function from 'geopandas' to return a fake GeoDataFrame.
    2. Load the mocked GeoDataFrame using 'gpd.read_file'.
    3. Call 'generate_uuid' to add a UUID column to the GeoDataFrame.
    4. Verify the following:
       - A 'uuid' column exists in the GeoDataFrame.
       - Each row in the GeoDataFrame has a unique UUID.
    """
    # Patch the 'gpd.read_file' function to return the mocked GeoDataFrame
    with patch("geopandas.read_file", return_value=mock_geojson):
        # Simulate loading a GeoJSON file (this will use the mocked data)
        shp = gpd.read_file("mock_url")
        # Call the 'generate_uuid' function to add UUIDs to the GeoDataFrame
        updated_shp = edmt.conversion.generate_uuid(shp)
        # Ensure that the 'uuid' column was added successfully
        assert "uuid" in updated_shp.columns, "The 'uuid' column should exist in the GeoDataFrame."
        # Ensure that all UUIDs are unique
        assert updated_shp["uuid"].nunique() == len(updated_shp), "All UUIDs should be unique for each row."





# def test_generate_uuid():
#     # Load the GeoJSON file
#     shp = gpd.read_file(
#         'https://www.dropbox.com/scl/fi/nzgus5jlvk8edktcf9nz5/Narok.geojson?rlkey=jufl5klgl6jftke8vprkze499&st=4incnanc&dl=1'
#     )

#     # Ensure the file is loaded correctly
#     assert not shp.empty, "GeoDataFrame should not be empty."

#     # Test the generate_uuid function
#     updated_shp = edmt.conversion.generate_uuid(shp)

#     # Ensure the UUID column exists
#     assert "uuid" in updated_shp.columns, "UUID column should be present in the GeoDataFrame."
#     assert updated_shp["uuid"].nunique() == len(updated_shp), "UUIDs should be unique for each row."
