drones_ = ["kml_to_geojson","get_utm_epsg"]
# @title **Convert KML to GeoJSON**

def kml_to_geojson(kml_file_path=None):
    kml_file_path = kml_file_path
    print(kml_file_path)
#   driver = ogr.GetDriverByName('KML')
#   dataSource = driver.Open(kml_file_path, 0)
#   if dataSource:
#       layer = dataSource.GetLayer()
#       geojson_driver = ogr.GetDriverByName('GeoJSON')
#       if os.path.exists(drone_file_path):
#           os.remove(drone_file_path)
#       geojson_ds = geojson_driver.CreateDataSource(drone_file_path)
#       geojson_ds.CopyLayer(layer, layer.GetName())
#       geojson_ds.Destroy()
#       dataSource.Destroy()


#   print(f"Downloaded & Converted {drone['name']} Trajectory to GeoJSON file")

# @title **UTM zone**
# Function to find UTM zone for a given longitude
def get_utm_epsg(longitude):
    zone_number = int((longitude + 180) / 6) + 1
    hemisphere = '6' if longitude >= 0 else '7'  # 6 for Northern, 7 for Southern Hemisphere
    return f"32{hemisphere}{zone_number:02d}"




