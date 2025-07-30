# import necessary libraries
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt
import folium
import contextily as ctx
import cartopy.crs as ccrs
from matplotlib_scalebar.scalebar import ScaleBar
import numpy as np
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, MultiLineString, MultiPoint
from typing import Union, Optional

class Map:
    def __init__(self, data, mode='static', width=800, height=600):
        """
        Initialize map with pre-loaded spatial data
        """
        self.data = data
        self.mode = mode
        self.width = width
        self.title = None
        self.heigth = height
    
    def set_projection(self, crs: str) -> 'Map':
        """
        Set the coordinate reference system for the map
        """
        if isinstance(self.data, gpd.GeoDataFrame):
            self.data = self.data.to_crs(crs)
            self.crs = crs
        return self
    
    def add_layer(self,layer_type: str, column: Optional[str] = None, **style) -> 'Map':
        """
        Add a layer to the map with optional styling
        """
        if layer_type not in ['point', 'line', 'polygon', 'raster']:
            raise ValueError("Supported layer types: polygons, points, lines, raster")
        if column and isinstance(self.data, gpd.GeoDataFrame) and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        layer = {
            'type': layer_type,
            'column': column,
            'style': style
        }
        self.layers.append(layer)
        return self
    
    def add_basemap(self, basemap: str = 'CartoDB.Positron', custom_tiles: Optional[str] = None, attr: Optional[str] = None) -> 'Map':
        """
        Add a basemap for static & interactive maps
        """
        valid_basemaps = [
            'CartoDB.Positron',
            'OpenStreetMap',
            'Stamen.Terrain',
            'Stamen.Toner',
            'Stamen.Watercolor']
        if custom_tiles:
            self.basemap = {'tiles': custom_tiles, 'attr': attr or "Custom"}
        elif basemap in valid_basemaps:
            self.basemap = basemap
        else:
            raise ValueError(f"Basemap must be one of {valid_basemaps} or provide custom_tiles and attr")
        return self
    
    def add_title(self, title: str) -> 'Map':
        """
        Add a title to the map
        """
        self.title = title
        return self
    
    def add_scale_bar(self, position: str = 'bottom-left', units: str = 'metric', scale: float = 1.0) -> 'Map':
        """
        Add a scale bar to the map
        """
        self.components['scale_bar'] = {
            'position': position,
            'units': units,
            'scale': scale
        }
        return self
    
    def add_compass(self, position: str = 'top-right', size: int = 50) -> 'Map':
        """
        Add a compass to the map
        """
        self.components['compass'] = {
            'position': position,
            'size': size
        }
        return self
    
    def add_legend(self, title: Optional[str] = None, position: str = 'bottom-right', labels: Optional[list] = None) -> 'Map':
        """
        Add a legend to the map
        """
        self.components['legend'] = {
            'title': title,
            'position': position,
            'labels': labels or []
        }
        return self