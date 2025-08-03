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
import logging
import requests
from xml.etree.ElementTree import ElementTree, fromstring
from matplotlib.colors import ListedColormap, to_hex
from urllib.parse import urlparse

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Map:
    # Fallback SVG if north_arrow.svg is missing or link fails
    FALLBACK_COMPASS_SVG = '''
    <svg width="50" height="50" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <path d="M50 10 L70 50 L50 90 L30 50 Z" fill="black"/>
      <text x="50" y="20" font-size="20" text-anchor="middle" fill="white">N</text>
    </svg>
    '''

    # Default compass SVG path as a local file path or URL
    DEFAULT_COMPASS_SVG_PATH = None  # Will use FALLBACK_COMPASS_SVG

    # Predefined basemaps
    PREDEFINED_BASEMAPS = {
        'World_Imagery': {
            'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}.png',
            'attr': 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
        },
        'OpenStreetMap': {
            'tiles': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'attr': '&copy; OpenStreetMap contributors'
        },
        'CartoDB_Positron': {
            'tiles': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
            'attr': '&copy; <a href="https://carto.com/attributions">CartoDB</a>'
        },
        'Stamen_Terrain': {
            'tiles': 'https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}{r}.png',
            'attr': '&copy; <a href="http://stamen.com">Stamen Design</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }
    }

    def __init__(self, data: Union[gpd.GeoDataFrame, str], mode: str = 'static', width: int = 800, height: int = 600):
        """
        Initialize a Map object with geospatial data.

        Args:
            data: GeoDataFrame or path to a GeoJSON/raster file.
            mode: 'static' for Matplotlib or 'interactive' for Folium.
            width: Width of the map in pixels.
            height: Height of the map in pixels.
        """
        if isinstance(data, str):
            if data.endswith('.geojson'):
                self.data = gpd.read_file(data)
                if self.data.empty:
                    raise ValueError("GeoJSON file is empty")
                self.crs = self.data.crs or "EPSG:4326"
            else:
                with rasterio.open(data) as src:
                    self.data = src
                    self.crs = src.crs.to_string() or "EPSG:4326"
        elif isinstance(data, gpd.GeoDataFrame):
            if data.empty:
                raise ValueError("GeoDataFrame is empty")
            if not data.geometry.is_valid.all():
                raise ValueError("GeoDataFrame contains invalid geometries")
            self.data = data
            self.crs = data.crs or "EPSG:4326"
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
        Reproject the data to the specified CRS.

        Args:
            crs: Target CRS (e.g., 'EPSG:4326').

        Returns:
            Self for method chaining.
        """
        if isinstance(self.data, gpd.GeoDataFrame):
            if self.data.crs is None:
                logger.warning("No CRS defined in data. Assuming EPSG:4326.")
                self.data.crs = "EPSG:4326"
            try:
                self.data = self.data.to_crs(crs)
                self.crs = crs
            except Exception as e:
                logger.error(f"Failed to reproject to {crs}: {e}")
                raise ValueError(f"Invalid CRS: {crs}")
        return self
    
    def add_points(self, column: Optional[str] = None, color: Union[str, list, dict] = 'red', alpha: float = 0.7, 
                   size: int = 10, marker_svg: Optional[str] = None, popup: bool = False) -> 'Map':
        """
        Add point geometries to the map.

        Args:
            column: Data column for coloring (optional).
            color: Color for points (string, list, or dict for categorical).
            alpha: Transparency (0 to 1).
            size: Marker size.
            marker_svg: Path or content of custom SVG marker.
            popup: Enable popups for interactive mode.

        Returns:
            Self for method chaining.
        """
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise ValueError("Data must be a GeoDataFrame to add points")
        if not any(self.data.geometry.type.isin(['Point', 'MultiPoint'])):
            raise ValueError("Data must contain Point or MultiPoint geometries")
        if column and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        if column and self.data[column].dtype not in ['int64', 'float64']:
            unique_values = self.data[column].unique()
            if isinstance(color, dict):
                colors = [color.get(val, 'red') for val in unique_values]
            else:
                colors = plt.cm.get_cmap('tab20', len(unique_values))(np.linspace(0, 1, len(unique_values)))
            color_map = dict(zip(unique_values, colors))
        else:
            colors = color
        
        layer = {
            'type': 'point',
            'column': column,
            'style': {'color': colors, 'alpha': alpha, 'size': size, 'marker_svg': marker_svg, 'color_map': color_map if column else None},
            'popup': popup
        }
        self.layers.append(layer)
        return self
    
    def add_polylines(self, column: Optional[str] = None, color: Union[str, list, dict] = 'blue', alpha: float = 0.7, 
                      linewidth: float = 2, popup: bool = False) -> 'Map':
        """
        Add polyline geometries to the map.

        Args:
            column: Data column for coloring (optional).
            color: Color for polylines (string, list, or dict for categorical).
            alpha: Transparency (0 to 1).
            linewidth: Line width.
            popup: Enable popups for interactive mode.

        Returns:
            Self for method chaining.
        """
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise ValueError("Data must be a GeoDataFrame to add polylines")
        if not any(self.data.geometry.type.isin(['LineString', 'MultiLineString'])):
            raise ValueError("Data must contain LineString or MultiLineString geometries")
        if column and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        if column and self.data[column].dtype not in ['int64', 'float64']:
            unique_values = self.data[column].unique()
            if isinstance(color, dict):
                colors = [color.get(val, 'blue') for val in unique_values]
            else:
                colors = plt.cm.get_cmap('tab20', len(unique_values))(np.linspace(0, 1, len(unique_values)))
            color_map = dict(zip(unique_values, colors))
        else:
            colors = color
        
        layer = {
            'type': 'line',
            'column': column,
            'style': {'color': colors, 'alpha': alpha, 'linewidth': linewidth, 'color_map': color_map if column else None},
            'popup': popup
        }
        self.layers.append(layer)
        return self
    
    def add_polygons(self, column: Optional[str] = None, color: Union[str, list, dict] = 'blue', alpha: float = 0.7, 
                     popup: bool = False) -> 'Map':
        """
        Add polygon geometries to the map.

        Args:
            column: Data column for coloring (optional).
            color: Color for polygons (string, list, or dict for categorical).
            alpha: Transparency (0 to 1).
            popup: Enable popups for interactive mode.

        Returns:
            Self for method chaining.
        """
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise ValueError("Data must be a GeoDataFrame to add polygons")
        if not any(self.data.geometry.type.isin(['Polygon', 'MultiPolygon'])):
            raise ValueError("Data must contain Polygon or MultiPolygon geometries")
        if column and column not in self.data.columns:
            raise ValueError(f"Column '{column}' not found in data")
        
        if column and self.data[column].dtype not in ['int64', 'float64']:
            unique_values = self.data[column].unique()
            if isinstance(color, dict):
                colors = [color.get(val, 'blue') for val in unique_values]
            else:
                colors = plt.cm.get_cmap('tab20', len(unique_values))(np.linspace(0, 1, len(unique_values)))
            color_map = dict(zip(unique_values, colors))
        else:
            n_counties = len(self.data)
            colors = plt.cm.get_cmap(color, n_counties)(np.linspace(0, 1, n_counties)) if isinstance(color, str) else color
            color_map = None
        
        layer = {
            'type': 'polygon',
            'column': column,
            'style': {'color': colors, 'alpha': alpha, 'color_map': color_map},
            'popup': popup
        }
        self.layers.append(layer)
        return self
    
    def add_raster(self, cmap: str = 'viridis', alpha: float = 1.0, bands: Optional[list] = None) -> 'Map':
        """
        Add a raster layer to the map.

        Args:
            cmap: Colormap for single-band rasters.
            alpha: Transparency (0 to 1).
            bands: List of band indices (1-based) to display.

        Returns:
            Self for method chaining.
        """
        if not isinstance(self.data, rasterio.io.DatasetReader):
            raise ValueError("Data must be a raster file to add raster layer")
        
        layer = {
            'type': 'raster',
            'column': None,
            'style': {'cmap': cmap, 'alpha': alpha, 'bands': bands or [1]}
        }
        self.layers.append(layer)
        return self
    
    def add_basemap(self, basemap: str = 'OpenStreetMap', custom_tiles: Optional[str] = None, 
                    attr: Optional[str] = None) -> 'Map':
        """
        Add a basemap to the map.

        Args:
            basemap: Predefined basemap name or 'custom' for custom tiles.
            custom_tiles: URL for custom tiles (if basemap='custom').
            attr: Attribution for custom tiles.

        Returns:
            Self for method chaining.
        """
        if custom_tiles:
            self.basemap = {'tiles': custom_tiles, 'attr': attr or "Custom"}
            logger.debug(f"Custom basemap added with tiles: {custom_tiles}")
        elif basemap in self.PREDEFINED_BASEMAPS:
            self.basemap = self.PREDEFINED_BASEMAPS[basemap]
            logger.debug(f"Predefined basemap '{basemap}' loaded successfully")
        else:
            raise ValueError(f"Basemap must be one of {list(self.PREDEFINED_BASEMAPS.keys())} or provide custom_tiles and attr")
        return self
    
    def add_title(self, title: str) -> 'Map':
        """
        Add a title to the map.

        Args:
            title: Title text.

        Returns:
            Self for method chaining.
        """
        self.title = title
        return self
    
    def add_scale_bar(self, position: str = 'bottom-left', units: str = 'km', scale: float = 1.0) -> 'Map':
        """
        Add a scale bar to the map (static mode only).

        Args:
            position: Position ('bottom-left', 'top-right', etc.).
            units: Units for the scale bar ('km', 'm', etc.).
            scale: Scale factor for the scale bar.

        Returns:
            Self for method chaining.
        """
        self.components['scale_bar'] = {
            'position': position,
            'units': units,
            'scale': scale
        }
        return self
    
    def add_compass(self, position: str = 'top-right', size: int = 50, 
                    custom_svg: Optional[str] = None, svg_url: Optional[str] = None) -> 'Map':
        """
        Add a compass/north arrow to the map.

        Args:
            position: Position ('top-right', 'top-left', etc.).
            size: Size of the compass in pixels.
            custom_svg: Path or content of custom SVG.
            svg_url: URL to fetch SVG from.

        Returns:
            Self for method chaining.
        """
        VALID_POSITIONS = ['top-right', 'top-left', 'bottom-right', 'bottom-left', 'top-center', 'bottom-center']
        if position not in VALID_POSITIONS:
            logger.warning(f"Invalid position '{position}'. Using 'top-right'.")
            position = 'top-right'
        
        svg_content = None
        if svg_url:
            try:
                response = requests.get(svg_url, timeout=10)
                response.raise_for_status()
                svg_content = response.text
                logger.debug(f"Fetched SVG content: {svg_content[:100]}...")
            except requests.RequestException as e:
                logger.error(f"Failed to fetch SVG from URL {svg_url}. Error: {e}")
                svg_content = self.FALLBACK_COMPASS_SVG
        elif custom_svg:
            if isinstance(custom_svg, str) and os.path.isfile(custom_svg):
                with open(custom_svg, 'r') as f:
                    svg_content = f.read()
                logger.debug(f"Using custom SVG from {custom_svg}")
            else:
                svg_content = custom_svg
                logger.debug(f"Using custom SVG content directly")
        else:
            svg_content = self.FALLBACK_COMPASS_SVG
            logger.debug("Using fallback SVG for compass")
        
        # Validate SVG
        try:
            ElementTree(fromstring(svg_content))
        except Exception as e:
            logger.error(f"Invalid SVG content: {e}. Using fallback SVG.")
            svg_content = self.FALLBACK_COMPASS_SVG
        
        self.components['compass'] = {
            'position': position,
            'size': size,
            'svg': svg_content
        }
        return self
    
    def add_legend(self, title: Optional[str] = None, position: str = 'bottom-right', 
                   labels: Optional[dict] = None) -> 'Map':
        """
        Add a legend to the map.

        Args:
            title: Legend title.
            position: Position ('bottom-right', 'top-left', etc.).
            labels: Dictionary of label-color pairs.

        Returns:
            Self for method chaining.
        """
        VALID_POSITIONS = ['top-right', 'top-left', 'bottom-right', 'bottom-left']
        if position not in VALID_POSITIONS:
            logger.warning(f"Invalid legend position '{position}'. Using 'bottom-right'.")
            position = 'bottom-right'
        self.components['legend'] = {
            'title': title,
            'position': position,
            'labels': labels or {}
        }
        return self
    
    def plot(self) -> Union[None, folium.Map]:
        """
        Plot the map in static or interactive mode.

        Returns:
            None for static mode, folium.Map for interactive mode.
        """
        if self.mode == 'static':
            self._plot_static()
        elif self.mode == 'interactive':
            return self._plot_interactive()
        else:
            raise ValueError("Mode must be 'static' or 'interactive'")
    
    def save(self, filename: str) -> None:
        """
        Save the map as an image (static) or HTML (interactive).

        Args:
            filename: Output file path (e.g., 'map.png' or 'map.html').
        """
        if self.mode == 'static':
            self._plot_static()
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Static map saved as {filename}")
        elif self.mode == 'interactive':
            m = self._plot_interactive()
            m.save(filename)
            logger.info(f"Interactive map saved as {filename}")
        else:
            raise ValueError("Mode must be 'static' or 'interactive'")
    
    def _plot_static(self) -> None:
        """
        Plot a static map using Matplotlib and Cartopy.
        """
        fig = plt.figure(figsize=(self.width / 100, self.height / 100))
        original_crs = self.crs
        if self.crs == 'EPSG:4326':
            ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        else:
            ax = fig.add_subplot(1, 1, 1, projection=ccrs.epsg(self.crs.split(':')[1]))
        
        for layer in self.layers:
            data = self.data
            cmap = None
            norm = None
            if layer['column'] and isinstance(data, gpd.GeoDataFrame):
                data = data.dropna(subset=[layer['column']])
                if data[layer['column']].dtype in ['int64', 'float64']:
                    cmap = plt.cm.get_cmap(layer['style']['color'] if isinstance(layer['style']['color'], str) else 'viridis')
                    norm = plt.Normalize(data[layer['column']].min(), data[layer['column']].max())
                    colors = cmap(norm(data[layer['column']]))
                else:
                    colors = layer['style']['color_map'] or layer['style']['color']
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
                data.plot(ax=ax, color=[to_hex(c) for c in colors] if isinstance(colors, np.ndarray) else colors, 
                          alpha=layer['style']['alpha'])
            elif layer['type'] == 'raster':
                with rasterio.open(self.data) as src:
                    if len(layer['style']['bands']) == 1:
                        plt.imshow(src.read(layer['style']['bands'][0]), cmap=layer['style']['cmap'], 
                                  alpha=layer['style']['alpha'], 
                                  extent=(src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top))
                    else:
                        img = np.stack([src.read(b) for b in layer['style']['bands']], axis=-1)
                        plt.imshow(img, alpha=layer['style']['alpha'], 
                                  extent=(src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top))
        
        if self.basemap:
            try:
                if self.crs != 'EPSG:4326' and isinstance(self.data, gpd.GeoDataFrame):
                    temp_data = self.data.to_crs('EPSG:4326')
                    temp_ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
                    ctx.add_basemap(temp_ax, source=self.basemap['tiles'], crs=ccrs.PlateCarree(), 
                                    attribution=self.basemap['attr'])
                    temp_ax.get_images()[0].set_axes(ax)
                    plt.delaxes(temp_ax)
                else:
                    ctx.add_basemap(ax, source=self.basemap['tiles'], crs=ccrs.PlateCarree(), 
                                    attribution=self.basemap['attr'])
                logger.debug(f"Basemap '{self.basemap['tiles']}' added successfully with CRS {self.crs}")
            except Exception as e:
                logger.error(f"Failed to add basemap '{self.basemap['tiles']}'. Error: {e}. Proceeding without basemap.")
                self.basemap = None
        
        if self.title:
            ax.set_title(self.title)
        
        if self.components['scale_bar']:
            ax.add_artist(ScaleBar(self.components['scale_bar']['scale'], 
                                  units=self.components['scale_bar']['units'],
                                  location=self.components['scale_bar']['position']))
        
        if self.components['compass'] and self.components['compass'].get('svg'):
            svg_content = self.components['compass']['svg']
            try:
                path = parse_path(svg_content)
                path = path.transformed(plt.matplotlib.transforms.Affine2D().scale(0.01 * self.components['compass']['size']))
                patch = PathPatch(path, facecolor='black', alpha=1.0)
                pos = {
                    'top-right': (0.95, 0.95),
                    'top-left': (0.05, 0.95),
                    'bottom-right': (0.95, 0.05),
                    'bottom-left': (0.05, 0.05),
                    'top-center': (0.5, 0.95),
                    'bottom-center': (0.5, 0.05)
                }[self.components['compass']['position']]
                ab = AnnotationBbox(OffsetImage(patch), pos, xycoords='axes fraction', frameon=False)
                ax.add_artist(ab)
                logger.debug(f"North arrow added at position {self.components['compass']['position']}")
            except Exception as e:
                logger.error(f"Failed to render north arrow. Error: {e}. Using fallback rendering.")
                ax.plot([0.95, 0.95, 0.9], [0.95, 0.9, 0.95], 'k-', transform=ax.transAxes)
        
        if self.components['legend']:
            if self.components['legend']['labels']:
                from matplotlib.lines import Line2D
                legend_elements = [Line2D([0], [0], color=color, label=label) 
                                  for label, color in self.components['legend']['labels'].items()]
                ax.legend(handles=legend_elements, title=self.components['legend']['title'], 
                         loc=self.components['legend']['position'])
            elif layer['column'] and cmap and norm:
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                plt.colorbar(sm, ax=ax, label=self.components['legend']['title'])
        
        plt.show()
    
    def _plot_interactive(self) -> folium.Map:
        """
        Plot an interactive map using Folium.

        Returns:
            folium.Map object.
        """
        if isinstance(self.data, gpd.GeoDataFrame):
            if self.crs == 'EPSG:4326':
                center = self.data.geometry.centroid.iloc[0].coords[0][::-1]
            else:
                try:
                    temp_data = self.data.to_crs('EPSG:4326')
                    center = temp_data.geometry.centroid.iloc[0].coords[0][::-1]
                except Exception as e:
                    logger.error(f"Failed to calculate centroid: {e}")
                    center = [0, 0]
        else:
            with rasterio.open(self.data) as src:
                center = [(src.bounds.top + src.bounds.bottom) / 2, (src.bounds.left + src.bounds.right) / 2]
        
        m = folium.Map(location=center, zoom_start=6, tiles=self.basemap['tiles'], attr=self.basemap['attr'], 
                       width=self.width, height=self.height)
        
        for layer in self.layers:
            data = self.data
            if layer['column'] and isinstance(data, gpd.GeoDataFrame):
                data = data.dropna(subset=[layer['column']])
                if data[layer['column']].dtype in ['int64', 'float64']:
                    norm = plt.Normalize(data[layer['column']].min(), data[layer['column']].max())
                    cmap = plt.cm.get_cmap(layer['style']['color'] if isinstance(layer['style']['color'], str) else 'viridis')
                    style_function = lambda feature: {
                        'color': to_hex(cmap(norm(feature['properties'][layer['column']]))),
                        'weight': layer['style'].get('linewidth', 2),
                        'opacity': layer['style']['alpha'],
                        'fillColor': to_hex(cmap(norm(feature['properties'][layer['column']]))),
                        'fillOpacity': layer['style']['alpha']
                    }
                else:
                    color_map = layer['style'].get('color_map', {})
                    style_function = lambda feature: {
                        'color': color_map.get(feature['properties'][layer['column']], 
                                              to_hex(layer['style']['color'])),
                        'weight': layer['style'].get('linewidth', 2),
                        'opacity': layer['style']['alpha'],
                        'fillColor': color_map.get(feature['properties'][layer['column']], 
                                                  to_hex(layer['style']['color'])),
                        'fillOpacity': layer['style']['alpha']
                    }
            else:
                style_function = lambda feature: {
                    'color': to_hex(layer['style']['color'] if isinstance(layer['style']['color'], np.ndarray) 
                                    else layer['style']['color']),
                    'weight': layer['style'].get('linewidth', 2),
                    'opacity': layer['style']['alpha'],
                    'fillColor': to_hex(layer['style']['color'] if isinstance(layer['style']['color'], np.ndarray) 
                                        else layer['style']['color']),
                    'fillOpacity': layer['style']['alpha']
                }
            
            if layer['type'] in ['line', 'polygon']:
                folium.GeoJson(
                    data,
                    style_function=style_function,
                    popup=folium.GeoJsonPopup(fields=[layer['column']] if layer['column'] and layer['popup'] else [])
                ).add_to(m)
            elif layer['type'] == 'point':
                if layer['style'].get('marker_svg'):
                    svg_content = layer['style']['marker_svg']
                    if os.path.isfile(svg_content):
                        with open(svg_content, 'r') as f:
                            svg_content = f.read()
                    icon = folium.features.CustomIcon(
                        icon_image=f"data:image/svg+xml;base64,{b64encode(svg_content.encode()).decode()}",
                        icon_size=(layer['style']['size'], layer['style']['size'])
                    )
                    for _, row in data.iterrows():
                        folium.Marker(
                            location=[row.geometry.y, row.geometry.x],
                            icon=icon,
                            popup=folium.Popup(str(row[layer['column']]) if layer['column'] and layer['popup'] else None)
                        ).add_to(m)
                else:
                    folium.GeoJson(
                        data,
                        marker=folium.CircleMarker(
                            radius=layer['style']['size'] / 2,
                            color=to_hex(layer['style']['color']),
                            fill=True,
                            fill_opacity=layer['style']['alpha']
                        ),
                        style_function=style_function,
                        popup=folium.GeoJsonPopup(fields=[layer['column']] if layer['column'] and layer['popup'] else [])
                    ).add_to(m)
            elif layer['type'] == 'raster':
                with rasterio.open(self.data) as src:
                    if len(layer['style']['bands']) == 1:
                        folium.raster_layers.ImageOverlay(
                            image=src.read(layer['style']['bands'][0]),
                            bounds=[[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]],
                            colormap=plt.cm.get_cmap(layer['style']['cmap']),
                            opacity=layer['style']['alpha']
                        ).add_to(m)
                    else:
                        img = np.stack([src.read(b) for b in layer['style']['bands']], axis=-1)
                        folium.raster_layers.ImageOverlay(
                            image=img,
                            bounds=[[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]],
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
                'bottom-left': 'position: absolute; bottom: 10px; left: 10px;',
                'top-center': 'position: absolute; top: 10px; left: 50%; transform: translateX(-50%);',
                'bottom-center': 'position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);'
            }[self.components['compass']['position']]
            compass_html = f'''
            <div style="{div_style}">
                <img src="data:image/svg+xml;base64,{b64encode(svg_content.encode()).decode()}" 
                     width="{self.components['compass']['size']}" 
                     height="{self.components['compass']['size']}">
            </div>
            '''
            m.get_root().html.add_child(folium.Element(compass_html))
        
        if self.components['legend']:
            if self.components['legend']['labels']:
                legend_html = f'''
                <div style="position: absolute; {self.components['legend']['position'].replace('-', ': ')}: 10px; 
                             background-color: white; padding: 5px; border: 1px solid black;">
                    <h4>{self.components['legend']['title']}</h4>
                    <ul>
                        {"".join([f'<li style="color: {color}">{label}</li>' 
                                  for label, color in self.components['legend']['labels'].items()])}
                    </ul>
                </div>
                '''
                m.get_root().html.add_child(folium.Element(legend_html))
            elif layer['column']:
                folium.map.LayerControl().add_to(m)
        
        return m