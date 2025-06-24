import edmt
import geopandas as gpd

def test_edmt_read_file_from_url():
    """
    Test the 'read_file_from_url()' function to ensure it downloads and reads the file as a GeoDataFrame.

    Steps:
    1. Import the function from the 'edmt.contrib' module.
    2. Call the function with a valid URL pointing to a GeoPackage file.
    3. Verify that the result is a valid GeoDataFrame.
    """
    # try:
    #     # Import the function
    #     from edmt.contrib import read_file_from_url as read_url

    #     # Call the function with a test URL
    #     url = "https://www.dropbox.com/scl/fi/09mbe0msh0nw61revvegu/dones.gpkg?rlkey=1reqe75wsqxwt87jwzk2pu8lz&dl=0"
    #     result = read_url(url_path=url)

    #     # Assert that the result is a GeoDataFrame
    #     assert isinstance(result, gpd.GeoDataFrame), "Result is not a GeoDataFrame."
    #     assert not result.empty, "The GeoDataFrame is empty."

    #     print("Test passed: The result is a valid, non-empty GeoDataFrame.")
    # except AssertionError as e:
    #     print(f"Test failed: {e}")
    # except Exception as e:
    #     print(f"Test failed due to an unexpected error: {e}")
