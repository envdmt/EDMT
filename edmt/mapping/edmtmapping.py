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
from matplotlib.patches import PathPatch
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from svgpath2mpl import parse_path
import io
import os
from pathlib import Path
from base64 import b64encode

class Map:
    # Fallback SVG if north_arrow.svg is missing
    FALLBACK_COMPASS_SVG = '''
    <svg width="50" height="50" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <path d="M50 10 L70 50 L50 90 L30 50 Z" fill="black"/>
      <text x="50" y="20" font-size="20" text-anchor="middle" fill="white">N</text>
    </svg>
    '''

    # Default compass SVG path (navigate from edmt/mapping to EDMT/assets)
    DEFAULT_COMPASS_SVG_PATH = str(Path(__file__).parent.parent.parent / 'assets' / 'north_arrow.svg')

    def __init__(self, data: Union[gpd.GeoDataFrame, str], mode: str = 'static', width: int = 800, height: int = 600):
        """
        Initialize map with pre-loaded spatial data, mode, and size.

        Parameters
        ----------
        data : GeoDataFrame or str
            Input GeoDataFrame or path to a raster file.
        mode : str, optional
            Map mode ('static' or 'interactive'). Default is 'static'.
        width : int, optional
            Map width in pixels. Default is 800.
        height : int, optional
            Map height in pixels. Default is 600.
        """
        if isinstance(data, str):
            if data.endswith('.geojson'):
                self.data = gpd.read_file(data)
                self.crs = self.data.crs
            else:
                with rasterio.open(data) as src:
                    self.data = src
                    self.crs = src.crs.to_string()
        elif isinstance(data, gpd.GeoDataFrame):
            self.data = data
            self.crs = data.crs
        else:
            raise ValueError("Data must be a GeoDataFrame or a path to a raster file or GeoJSON")
        
        if mode not in ['static', 'interactive']:
            raise ValueError("Mode must be 'static' or 'interactive'")
        
        self.mode = mode
        self.width = width
        self.height = height
        self.layers = []
        self.components = {'scale_bar': None, 'compass': None, 'legend': None}
        self.basemap = None
        self.title = None
    
    def set_projection(self, crs: str) -> 'Map':
        """
        Set the coordinate reference system for the map.
        """
        if isinstance(self.data, gpd.GeoDataFrame):
            self.data = self.data.to_crs(crs)
            self.crs = crs
        return self
    
    def add_points(self, column: Optional[str] = None, color: str = 'red', alpha: float = 0.7, size: int = 10, marker_svg: Optional[str] = None) -> 'Map':
        """
        Add a point layer to the map with optional custom SVG marker.

        Parameters
        ----------
        column : str, optional
            Column name for point attributes. Default is None.
        color : str, optional
            Color or colormap name. Default is 'red'.
        alpha : float, optional
            Transparency (0 to 1). Default is 0.7.
        size : int, optional
            Point size (pixels for static, radius for interactive). Default is 10.
        marker_svg : str, optional
            Path to a custom SVG file or SVG string for point markers. Default is None (uses circle).
        """
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise ValueError("Data must be a GeoDataFrame to add points")
        if not any(self.data.geometry.type.isin(['Point', 'MultiPoint'])):
            raise ValueError("Data must contain Point or MultiPoint geometries")
        if column and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        layer = {
            'type': 'point',
            'column': column,
            'style': {'color': color, 'alpha': alpha, 'size': size, 'marker_svg': marker_svg}
        }
        self.layers.append(layer)
        return self
    
    def add_polylines(self, column: Optional[str] = None, color: str = 'blue', alpha: float = 0.7, linewidth: float = 2) -> 'Map':
        """
        Add a polyline layer to the map.
        """
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise ValueError("Data must be a GeoDataFrame to add polylines")
        if not any(self.data.geometry.type.isin(['LineString', 'MultiLineString'])):
            raise ValueError("Data must contain LineString or MultiLineString geometries")
        if column and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        layer = {
            'type': 'line',
            'column': column,
            'style': {'color': color, 'alpha': alpha, 'linewidth': linewidth}
        }
        self.layers.append(layer)
        return self
    
    def add_polygons(self, column: Optional[str] = None, color: str = 'viridis', alpha: float = 0.7) -> 'Map':
        """
        Add a polygon layer to the map.
        """
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise ValueError("Data must be a GeoDataFrame to add polygons")
        if not any(self.data.geometry.type.isin(['Polygon', 'MultiPolygon'])):
            raise ValueError("Data must contain Polygon or MultiPolygon geometries")
        if column and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        layer = {
            'type': 'polygon',
            'column': column,
            'style': {'color': color, 'alpha': alpha}
        }
        self.layers.append(layer)
        return self
    
    def add_raster(self, cmap: str = 'viridis', alpha: float = 1.0) -> 'Map':
        """
        Add a raster layer to the map.
        """
        if not isinstance(self.data, rasterio.io.DatasetReader):
            raise ValueError("Data must be a raster file to add raster layer")
        
        layer = {
            'type': 'raster',
            'column': None,
            'style': {'cmap': cmap, 'alpha': alpha}
        }
        self.layers.append(layer)
        return self
    
    def add_basemap(self, basemap: str = 'CartoDB.Positron', custom_tiles: Optional[str] = None, attr: Optional[str] = None) -> 'Map':
        """
        Add a basemap for static & interactive maps.
        """
        valid_basemaps = [
            'CartoDB.Positron',
            'OpenStreetMap',
            'Stamen.Terrain',
            'Stamen.Toner',
            'Stamen.Watercolor'
        ]
        if custom_tiles:
            self.basemap = {'tiles': custom_tiles, 'attr': attr or "Custom"}
        elif basemap in valid_basemaps:
            self.basemap = basemap
        else:
            raise ValueError(f"Basemap must be one of {valid_basemaps} or provide custom_tiles and attr")
        return self
    
    def add_title(self, title: str) -> 'Map':
        """
        Add a title to the map.
        """
        self.title = title
        return self
    
    def add_scale_bar(self, position: str = 'bottom-left', units: str = 'metric', scale: float = 1.0) -> 'Map':
        """
        Add a scale bar to the map.
        """
        self.components['scale_bar'] = {
            'position': position,
            'units': units,
            'scale': scale
        }
        return self
    
    def add_compass(self, position: str = 'top-right', size: int = 50, custom_svg: Optional[str] = None) -> 'Map':
        """
        Add a compass to the map, using default EDMT SVG or custom SVG.

        Parameters
        ----------
        position : str, optional
            Position of the compass ('top-right', 'top-left', 'bottom-right', 'bottom-left'). Default is 'top-right'.
        size : int, optional
            Size of the compass in pixels. Default is 50.
        custom_svg : str, optional
            Path to a custom SVG file or SVG string. If None, uses default EDMT compass SVG.
        """
        if custom_svg:
            if os.path.isfile(custom_svg):
                with open(custom_svg, 'r') as f:
                    svg_content = f.read()
            else:
                svg_content = custom_svg
        else:
            if os.path.isfile(self.DEFAULT_COMPASS_SVG_PATH):
                with open(self.DEFAULT_COMPASS_SVG_PATH, 'r') as f:
                    svg_content = f.read()
            else:
                svg_content = self.FALLBACK_COMPASS_SVG
        
        self.components['compass'] = {
            'position': position,
            'size': size,
            'svg': svg_content
        }
        return self
    
    def add_legend(self, title: Optional[str] = None, position: str = 'bottom-right', labels: Optional[list] = None) -> 'Map':
        """
        Add a legend to the map.
        """
        self.components['legend'] = {
            'title': title,
            'position': position,
            'labels': labels or []
        }
        return self
    
    def plot(self) -> Union[None, folium.Map]:
        """
        Plot the map based on the initialized mode.
        """
        if self.mode == 'static':
            self._plot_static()
        elif self.mode == 'interactive':
            return self._plot_interactive()
        else:
            raise ValueError("Mode must be 'static' or 'interactive'")
    
    def _plot_static(self) -> None:
        """
        Render a static map using matplotlib and cartopy.
        """
        fig = plt.figure(figsize=(self.width / 100, self.height / 100))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.epsg(self.crs.split(':')[1]) if self.crs else ccrs.PlateCarree())
        
        for layer in self.layers:
            data = self.data
            if layer['column'] and isinstance(data, gpd.GeoDataFrame):
                data = data.dropna(subset=[layer['column']])
                if data[layer['column']].dtype in ['int64', 'float64']:
                    cmap = plt.cm.get_cmap(layer['style']['color'])
                    norm = plt.Normalize(data[layer['column']].min(), data[layer['column']].max())
                    colors = cmap(norm(data[layer['column']]))
                else:
                    colors = layer['style']['color']
            else:
                colors = layer['style']['color']
            
            if layer['type'] == 'point':
                if layer['style'].get('marker_svg'):
                    svg_content = layer['style']['marker_svg']
                    if os.path.isfile(svg_content):
                        with open(svg_content, 'r') as f:
                            svg_content = f.read()
                    path = parse_path(svg_content)
                    path = path.transformed(plt.matplotlib.transforms.Affine2D().scale(0.01 * layer['style']['size']))
                    for idx, row in data.iterrows():
                        x, y = row.geometry.x, row.geometry.y
                        color = colors[idx] if isinstance(colors, np.ndarray) else colors
                        patch = PathPatch(path, facecolor=color, alpha=layer['style']['alpha'])
                        ab = AnnotationBbox(OffsetImage(patch), (x, y), frameon=False)
                        ax.add_artist(ab)
                else:
                    data.plot(ax=ax, color=colors, alpha=layer['style']['alpha'], markersize=layer['style']['size'])
            elif layer['type'] == 'line':
                data.plot(ax=ax, color=colors, alpha=layer['style']['alpha'], linewidth=layer['style']['linewidth'])
            elif layer['type'] == 'polygon':
                data.plot(ax=ax, color=colors, alpha=layer['style']['alpha'])
            elif layer['type'] == 'raster':
                with rasterio.open(self.data) as src:
                    plt.imshow(src.read(1), cmap=layer['style']['cmap'], alpha=layer['style']['alpha'], 
                              extent=(src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top))
        
        if self.basemap:
            if isinstance(self.basemap, dict):
                ctx.add_basemap(ax, source=self.basemap['tiles'], attribution=self.basemap['attr'], crs=self.crs)
            else:
                ctx.add_basemap(ax, source=ctx.providers.__dict__[self.basemap.replace('.', '_')], crs=self.crs)
        
        if self.title:
            ax.set_title(self.title)
        
        if self.components['scale_bar']:
            ax.add_artist(ScaleBar(self.components['scale_bar']['scale'], 
                                  units=self.components['scale_bar']['units'],
                                  location=self.components['scale_bar']['position']))
        
        if self.components['compass']:
            svg_content = self.components['compass']['svg']
            path = parse_path(svg_content)
            path = path.transformed(plt.matplotlib.transforms.Affine2D().scale(0.01 * self.components['compass']['size']))
            patch = PathPatch(path, facecolor='black', alpha=1.0)
            pos = {
                'top-right': (0.95, 0.95),
                'top-left': (0.05, 0.95),
                'bottom-right': (0.95, 0.05),
                'bottom-left': (0.05, 0.05)
            }[self.components['compass']['position']]
            ab = AnnotationBbox(OffsetImage(patch), pos, xycoords='axes fraction', frameon=False)
            ax.add_artist(ab)
        
        if self.components['legend'] and layer['column']:
            sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
            plt.colorbar(sm, ax=ax, label=self.components['legend']['title'])
        
        plt.show()
    
    def _plot_interactive(self) -> folium.Map:
        """
        Render an interactive map using folium.
        """
        if isinstance(self.data, gpd.GeoDataFrame):
            center = self.data.geometry.centroid.iloc[0].coords[0][::-1]
        else:
            with rasterio.open(self.data) as src:
                center = [(src.bounds.top + src.bounds.bottom) / 2, (src.bounds.left + src.bounds.right) / 2]
        
        m = folium.Map(location=center, zoom_start=6, tiles=self.basemap['tiles'] if isinstance(self.basemap, dict) else self.basemap,
                       attr=self.basemap['attr'] if isinstance(self.basemap, dict) else None, width=self.width, height=self.height)
        
        for layer in self.layers:
            data = self.data
            if layer['column'] and isinstance(data, gpd.GeoDataFrame):
                data = data.dropna(subset=[layer['column']])
                if data[layer['column']].dtype in ['int64', 'float64']:
                    style_function = lambda x: {
                        'fillColor': plt.cm.get_cmap(layer['style']['color'])(
                            (x['properties'][layer['column']] - data[layer['column']].min()) /
                            (data[layer['column']].max() - data[layer['column']].min())
                        ),
                        'color': 'black',
                        'weight': 1,
                        'fillOpacity': layer['style']['alpha']
                    }
                else:
                    style_function = lambda x: {
                        'fillColor': layer['style']['color'],
                        'color': 'black',
                        'weight': 1,
                        'fillOpacity': layer['style']['alpha']
                    }
            else:
                style_function = lambda x: {
                    'fillColor': layer['style']['color'],
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': layer['style']['alpha']
                }
            
            if layer['type'] == 'point':
                for _, row in data.iterrows():
                    if layer['style'].get('marker_svg'):
                        svg_content = layer['style']['marker_svg']
                        if os.path.isfile(svg_content):
                            with open(svg_content, 'r') as f:
                                svg_content = f.read()
                        icon_size = (layer['style']['size'], layer['style']['size'])
                        icon = folium.features.CustomIcon(
                            icon_image=f"data:image/svg+xml;base64,{b64encode(svg_content.encode()).decode()}",
                            icon_size=icon_size
                        )
                        folium.Marker(
                            location=[row.geometry.y, row.geometry.x],
                            icon=icon,
                            popup=folium.Popup(str(row[layer['column']]) if layer['column'] else None)
                        ).add_to(m)
                    else:
                        folium.CircleMarker(
                            location=[row.geometry.y, row.geometry.x],
                            radius=layer['style']['size'] / 2,
                            color=style_function({'properties': row})['fillColor'],
                            fill=True,
                            fill_opacity=layer['style']['alpha'],
                            popup=folium.Popup(str(row[layer['column']]) if layer['column'] else None)
                        ).add_to(m)
            elif layer['type'] == 'line':
                folium.GeoJson(
                    data,
                    style_function=style_function,
                    popup=folium.GeoJsonPopup(fields=[layer['column']] if layer['column'] else [])
                ).add_to(m)
            elif layer['type'] == 'polygon':
                folium.GeoJson(
                    data,
                    style_function=style_function,
                    popup=folium.GeoJsonPopup(fields=[layer['column']] if layer['column'] else [])
                ).add_to(m)
            elif layer['type'] == 'raster':
                with rasterio.open(self.data) as src:
                    folium.raster_layers.ImageOverlay(
                        image=src.read(1),
                        bounds=[[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]],
                        colormap=plt.cm.get_cmap(layer['style']['cmap']),
                        opacity=layer['style']['alpha']
                    ).add_to(m)
        
        if self.title:
            title_html = f'<h3 align="center" style="font-size:16px"><b>{self.title}</b></h3>'
            m.get_root().html.add_child(folium.Element(title_html))
        
        if self.components['compass']:
            svg_content = self.components['compass']['svg']
            div_style = {
                'top-right': 'position: absolute; top: 10px; right: 10px;',
                'top-left': 'position: absolute; top: 10px; left: 10px;',
                'bottom-right': 'position: absolute; bottom: 10px; right: 10px;',
                'bottom-left': 'position: absolute; bottom: 10px; left: 10px;'
            }[self.components['compass']['position']]
            compass_html = f'''
            <div style="{div_style}">
                <img src="data:image/svg+xml;base64,{b64encode(svg_content.encode()).decode()}" 
                     width="{self.components['compass']['size']}" 
                     height="{self.components['compass']['size']}">
            </div>
            '''
            m.get_root().html.add_child(folium.Element(compass_html))
        
        if self.components['legend'] and layer['column']:
            folium.map.LayerControl().add_to(m)
        
        return m