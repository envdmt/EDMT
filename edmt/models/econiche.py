import pandas as pd
import pillow
import rasterio


def create_raster():
    data = {
        'Band1': [1, 2, 3],
        'Band2': [4, 5, 6],
        'Band3': [7, 8, 9]
    }
    raster = rasterio.open('example.tif', 'w', driver='GTiff', height=3, width=3, count=3, dtype='int32')
    raster.write(pd.DataFrame(data).values.reshape(3, 3, 3))
    raster.close()
    print("Raster created")
    return 'example.tif'