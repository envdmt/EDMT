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
import re
from matplotlib.colors import ListedColormap, to_hex
from urllib.parse import urlparse
import warnings
import importlib.util

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Map:
    # Fallback SVG for north arrow
    FALLBACK_COMPASS_SVG = '''
    <svg width="50" height="50" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <path d="M50 10 L70 50 L50 90 L30 50 Z" fill="black"/>
      <text x="50" y="20" font-size="20" text-anchor="middle" fill="white">N</text>
    </svg>
    '''

    # Default compass SVG URL
    DEFAULT_COMPASS_SVG_URL = "https://www.dropbox.com/scl/fi/89gojqdhfbd59keuambfl/north-arrow.svg?rlkey=f4sj84830ow4uurz9z6duyu7m&st=rz67uof2&dl=1"

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
        # Check dependencies
        required = ['geopandas', 'rasterio', 'matplotlib', 'folium', 'contextily', 'cartopy', 'shapely', 'svgpath2mpl']
        for pkg in required:
            if not importlib.util.find_spec(pkg):
                raise ImportError(f"Required package '{pkg}' not found. Please install it.")

        if isinstance(data, str):
            if data.endswith('.geojson'):
                self.data = gpd.read_file(data)
                self.crs = self.data.crs if self.data.crs else 'EPSG:4326'
            else:
                with rasterio.open(data) as src:
                    self.data = src
                    self.crs = src.crs.to_string() if src.crs else 'EPSG:4326'
        elif isinstance(data, gpd.GeoDataFrame):
            self.data = data
            self.crs = data.crs if data.crs else 'EPSG:4326'
        else:
            raise ValueError("Data must be a GeoDataFrame or a path to a raster file or GeoJSON")

        if not isinstance(self.crs, str) or not self.crs.startswith('EPSG:'):
            logger.warning(f"Invalid or unsupported CRS: {self.crs}. Defaulting to EPSG:4326")
            self.crs = 'EPSG:4326'

        if mode not in ['static', 'interactive']:
            raise ValueError("Mode must be 'static' or 'interactive'")

        self.mode = mode
        self.width = width
        self.height = height
        self.layers = []
        self.components = {'scale_bar': None, 'compass': None, 'legend': None}
        self.basemap = None
        self.title = None
        self._colormap_cache = {}  # Cache for colormaps

    def set_projection(self, crs: str) -> 'Map':
        if not isinstance(crs, str) or not crs.startswith('EPSG:'):
            logger.warning(f"Invalid CRS: {crs}. Keeping current CRS: {self.crs}")
            return self
        if isinstance(self.data, gpd.GeoDataFrame):
            try:
                self.data = self.data.to_crs(crs)
                self.crs = crs
            except Exception as e:
                logger.error(f"Failed to reproject to {crs}: {e}")
                warnings.warn(f"Failed to reproject to {crs}. Keeping original CRS.")
        return self

    def add_points(self, column: Optional[str] = None, color: str = 'red', alpha: float = 0.7, size: int = 10, marker_svg: Optional[str] = None) -> 'Map':
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

    def add_raster(self, cmap: str = 'viridis', alpha: float = 1.0, bands: Optional[list] = None) -> 'Map':
        if not isinstance(self.data, rasterio.io.DatasetReader):
            raise ValueError("Data must be a raster file to add raster layer")
        layer = {
            'type': 'raster',
            'column': None,
            'style': {'cmap': cmap, 'alpha': alpha, 'bands': bands or [1]}
        }
        self.layers.append(layer)
        return self

    def add_basemap(self, basemap: str = 'OpenStreetMap', custom_tiles: Optional[str] = None, attr: Optional[str] = None) -> 'Map':
        if custom_tiles:
            try:
                response = requests.head(custom_tiles, timeout=5)
                if response.status_code != 200:
                    raise ValueError(f"Invalid custom basemap URL: {custom_tiles}")
                self.basemap = {'tiles': custom_tiles, 'attr': attr or "Custom"}
                logger.debug(f"Custom basemap added with tiles: {custom_tiles}")
            except requests.RequestException as e:
                logger.error(f"Failed to validate custom basemap URL {custom_tiles}: {e}")
                warnings.warn("Invalid custom basemap URL. Defaulting to OpenStreetMap.")
                self.basemap = self.PREDEFINED_BASEMAPS['OpenStreetMap']
        elif basemap in self.PREDEFINED_BASEMAPS:
            self.basemap = self.PREDEFINED_BASEMAPS[basemap]
            logger.debug(f"Predefined basemap '{basemap}' loaded successfully")
        else:
            raise ValueError(f"Basemap must be one of {list(self.PREDEFINED_BASEMAPS.keys())} or provide custom_tiles and attr")
        return self

    def add_title(self, title: str) -> 'Map':
        self.title = title
        return self

    def add_scale_bar(self, position: str = 'bottom-left', units: str = 'metric', scale: float = 1.0) -> 'Map':
        self.components['scale_bar'] = {
            'position': position,
            'units': units,
            'scale': scale
        }
        return self

    def add_compass(self, position: str = 'top-right', size: int = 50, custom_svg: Optional[str] = None, svg_url: Optional[str] = None) -> 'Map':
        svg_content = None
        try:
            if svg_url:
                response = requests.get(svg_url, timeout=10)
                response.raise_for_status()
                svg_content = response.text
                logger.debug(f"Fetched SVG content from {svg_url}: {svg_content[:100]}...")
            elif custom_svg:
                if os.path.isfile(custom_svg):
                    with open(custom_svg, 'r') as f:
                        svg_content = f.read()
                    logger.debug(f"Loaded custom SVG from {custom_svg}")
                else:
                    svg_content = custom_svg
                    logger.debug("Using provided SVG content directly")
            else:
                response = requests.get(self.DEFAULT_COMPASS_SVG_URL, timeout=10)
                response.raise_for_status()
                svg_content = response.text
                logger.debug(f"Fetched default SVG from {self.DEFAULT_COMPASS_SVG_URL}: {svg_content[:100]}...")

            # Validate SVG content
            if not svg_content or not isinstance(svg_content, str):
                raise ValueError("SVG content is empty or invalid")
            path_match = re.search(r'd="([^"]*)"', svg_content)
            if not path_match or not re.search(r'[MLCSQTAZmlcsqta][0-9\.\-,]+', path_match.group(1)):
                logger.warning("Invalid SVG path data. Using fallback SVG.")
                svg_content = self.FALLBACK_COMPASS_SVG

        except (requests.RequestException, ValueError, IOError) as e:
            logger.error(f"Failed to load SVG: {e}. Using fallback SVG.")
            svg_content = self.FALLBACK_COMPASS_SVG

        self.components['compass'] = {
            'position': position,
            'size': size,
            'svg': svg_content
        }
        return self

    def add_legend(self, title: Optional[str] = None, position: str = 'bottom-right', labels: Optional[list] = None) -> 'Map':
        self.components['legend'] = {
            'title': title,
            'position': position,
            'labels': labels or []
        }
        return self

    def _get_colormap(self, layer, data):
        """Helper to generate or retrieve cached colormap for a layer."""
        cache_key = (layer['type'], layer['column'], layer['style']['color'])
        if cache_key in self._colormap_cache:
            return self._colormap_cache[cache_key]

        if layer['column'] and isinstance(data, gpd.GeoDataFrame):
            data = data.dropna(subset=[layer['column']])
            if data[layer['column']].dtype in ['int64', 'float64']:
                cmap = plt.colormaps.get_cmap(layer['style']['color'])
                norm = plt.Normalize(data[layer['column']].min(), data[layer['column']].max())
                colors = cmap(norm(data[layer['column']]))
                self._colormap_cache[cache_key] = (colors, cmap, norm)
                return colors, cmap, norm
            else:
                n_items = len(data)
                colors = layer['style']['color'] if isinstance(layer['style']['color'], np.ndarray) else plt.colormaps.get_cmap(layer['style']['color'], n_items)(np.linspace(0, 1, n_items))
                self._colormap_cache[cache_key] = (colors, None, None)
                return colors, None, None
        else:
            n_items = len(data)
            colors = layer['style']['color'] if isinstance(layer['style']['color'], np.ndarray) else plt.colormaps.get_cmap(layer['style']['color'], n_items)(np.linspace(0, 1, n_items))
            self._colormap_cache[cache_key] = (colors, None, None)
            return colors, None, None

    def _plot_static(self) -> None:
        fig = plt.figure(figsize=(self.width / 100, self.height / 100))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree() if self.crs == 'EPSG:4326' else ccrs.epsg(self.crs.split(':')[1]))

        # Simplify geometries for performance
        if isinstance(self.data, gpd.GeoDataFrame):
            self.data['geometry'] = self.data.geometry.simplify(tolerance=0.01, preserve_topology=True)

        for layer in self.layers:
            data = self.data
            colors, cmap, norm = self._get_colormap(layer, data)

            if layer['type'] == 'point':
                if layer['style'].get('marker_svg'):
                    try:
                        svg_content = layer['style']['marker_svg']
                        if os.path.isfile(svg_content):
                            with open(svg_content, 'r') as f:
                                svg_content = f.read()
                        path = parse_path(svg_content)
                        path = path.transformed(plt.matplotlib.transforms.Affine2D().scale(0.01 * layer['style']['size']))
                        for idx, row in data.iterrows():
                            x, y = row.geometry.x, row.geometry.y
                            color = colors[idx] if isinstance(colors, np.ndarray) else colors
                            patch = PathPatch(path, facecolor=to_hex(color), alpha=layer['style']['alpha'])
                            ab = AnnotationBbox(OffsetImage(patch), (x, y), frameon=False)
                            ax.add_artist(ab)
                    except Exception as e:
                        logger.error(f"Failed to render marker SVG: {e}. Using default markers.")
                        data.plot(ax=ax, color=colors, alpha=layer['style']['alpha'], markersize=layer['style']['size'])
                else:
                    data.plot(ax=ax, color=colors, alpha=layer['style']['alpha'], markersize=layer['style']['size'])
            elif layer['type'] == 'line':
                data.plot(ax=ax, color=colors, alpha=layer['style']['alpha'], linewidth=layer['style']['linewidth'])
            elif layer['type'] == 'polygon':
                data.plot(ax=ax, color=[to_hex(c) for c in colors], alpha=layer['style']['alpha'])
            elif layer['type'] == 'raster':
                with rasterio.open(self.data) as src:
                    if len(layer['style']['bands']) > 1:  # Multi-band (e.g., RGB)
                        img = np.dstack([src.read(b) for b in layer['style']['bands']])
                        plt.imshow(img, extent=(src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top))
                    else:
                        plt.imshow(src.read(layer['style']['bands'][0]), cmap=layer['style']['cmap'], alpha=layer['style']['alpha'],
                                  extent=(src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top))

        if self.basemap:
            try:
                if self.crs != 'EPSG:4326' and isinstance(self.data, gpd.GeoDataFrame):
                    temp_data = self.data.to_crs('EPSG:4326')
                    temp_ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
                    ctx.add_basemap(temp_ax, source=self.basemap['tiles'], crs=ccrs.PlateCarree(), attribution=self.basemap['attr'])
                    temp_ax.get_images()[0].set_axes(ax)
                    plt.delaxes(temp_ax)
                else:
                    ctx.add_basemap(ax, source=self.basemap['tiles'], crs=ccrs.PlateCarree(), attribution=self.basemap['attr'])
                logger.debug(f"Basemap '{self.basemap['tiles']}' added successfully")
            except Exception as e:
                logger.error(f"Failed to add basemap: {e}. Proceeding without basemap.")
                warnings.warn("Failed to add basemap. Proceeding without basemap.")

        if self.title:
            ax.set_title(self.title)

        if self.components['scale_bar']:
            ax.add_artist(ScaleBar(self.components['scale_bar']['scale'],
                                  units=self.components['scale_bar']['units'],
                                  location=self.components['scale_bar']['position']))

        if self.components['compass'] and self.components['compass'].get('svg'):
            try:
                path = parse_path(self.components['compass']['svg'])
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
                logger.debug(f"North arrow added at {self.components['compass']['position']}")
            except Exception as e:
                logger.error(f"Failed to render north arrow: {e}. Using fallback rendering.")
                ax.plot([0.95, 0.95, 0.9], [0.95, 0.9, 0.95], 'k-', transform=ax.transAxes)

        if self.components['legend'] and any(layer['column'] for layer in self.layers):
            for layer in self.layers:
                if layer['column']:
                    colors, cmap, norm = self._get_colormap(layer, self.data)
                    if cmap and norm:
                        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                        plt.colorbar(sm, ax=ax, label=self.components['legend']['title'] or layer['column'])
                    break  # Only add one legend for now

        plt.show()

    def _plot_interactive(self) -> folium.Map:
        if isinstance(self.data, gpd.GeoDataFrame):
            center = self.data.geometry.centroid.iloc[0].coords[0][::-1]
        else:
            with rasterio.open(self.data) as src:
                center = [(src.bounds.top + src.bounds.bottom) / 2, (src.bounds.left + src.bounds.right) / 2]

        m = folium.Map(location=center, zoom_start=6, tiles=self.basemap['tiles'], attr=self.basemap['attr'], width=self.width, height=self.height)

        for layer in self.layers:
            data = self.data
            colors, _, _ = self._get_colormap(layer, data)
            style_function = lambda x, idx=data.index.get_loc(x['properties'][layer['column']] if layer['column'] else x['id']): {
                'fillColor': to_hex(colors[idx]),
                'color': 'black',
                'weight': 1,
                'fillOpacity': layer['style']['alpha']
            }

            if layer['type'] == 'point' and not layer['style'].get('marker_svg'):
                folium.GeoJson(
                    data,
                    marker=folium.CircleMarker(radius=layer['style']['size'] / 2, color=layer['style']['color'], fill_opacity=layer['style']['alpha']),
                    popup=folium.GeoJsonPopup(fields=[layer['column']] if layer['column'] else [])
                ).add_to(m)
            elif layer['type'] == 'point':
                for _, row in data.iterrows():
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
            elif layer['type'] in ['line', 'polygon']:
                folium.GeoJson(
                    data,
                    style_function=style_function,
                    popup=folium.GeoJsonPopup(fields=[layer['column']] if layer['column'] else [])
                ).add_to(m)
            elif layer['type'] == 'raster':
                with rasterio.open(self.data) as src:
                    if len(layer['style']['bands']) > 1:
                        img = np.dstack([src.read(b) for b in layer['style']['bands']])
                        colormap = None
                    else:
                        img = src.read(layer['style']['bands'][0])
                        colormap = plt.colormaps.get_cmap(layer['style']['cmap'])
                    folium.raster_layers.ImageOverlay(
                        image=img,
                        bounds=[[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]],
                        colormap=colormap,
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

        if self.components['legend'] and any(layer['column'] for layer in self.layers):
            colors, _, _ = self._get_colormap(self.layers[-1], self.data)
            legend_html = f'''
            <div style="position: fixed; {self.components['legend']['position']}; z-index:9999; background-color:white; padding:5px;">
                <h4>{self.components['legend']['title'] or 'Legend'}</h4>
                {''.join([f'<p>{label}: <span style="background-color:{to_hex(color)}">&nbsp;&nbsp;</span></p>' for label, color in zip(self.components['legend']['labels'] or data.index, colors)])}
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))

        folium.map.LayerControl().add_to(m)
        return m

    def plot(self) -> Union[None, folium.Map]:
        if self.mode == 'static':
            self._plot_static()
        elif self.mode == 'interactive':
            return self._plot_interactive()
        else:
            raise ValueError("Mode must be 'static' or 'interactive'")