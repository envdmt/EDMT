drones_ = ["kml_to_geojson","get_utm_epsg"]

from osgeo import ogr
import os

def kml_to_geojson(file_path=None,url=None):
    if file_path and url is None:
        print("file path and url invalid.")
    else:
        driver = ogr.GetDriverByName('KML')
        dataSource = driver.Open(file_path or url, 0)

        if dataSource:
            layer = dataSource.GetLayer()
            geojson_driver = ogr.GetDriverByName('GeoJSON')
            output_folder = f"Drone - {file_path}"

            if os.path.exists(output_folder):
                os.remove(output_folder)
            geojson_ds = geojson_driver.CreateDataSource(output_folder)
            geojson_ds.CopyLayer(layer, layer.GetName())
            geojson_ds.Destroy()
            dataSource.Destroy()
            print(f"Successuflly Converted KML to GeoJSON and saved to {output_folder}")
       

# Function to find UTM zone for a given longitude
def get_utm_epsg(longitude=None):
    if longitude is None:
       print("KeyError : Select column with longitude values")
    else:
        zone_number = int((longitude + 180) / 6) + 1
        hemisphere = '6' if longitude >= 0 else '7'  # 6 for Northern, 7 for Southern Hemisphere
        return f"32{hemisphere}{zone_number:02d}"
