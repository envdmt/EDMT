import leafmap





class Mapping:
    def __init__(self, zoom=None, height=None, width=None, **kwargs):
        default_params = {
            'draw_control': False,
            'measure_control': False,
            'fullscreen_control': False,
            'attribution_control': False,
        }
        default_params.update(kwargs)
        default_params.update({
            'zoom': zoom,
            'height': height,
            'width': width
        })
        self.map = leafmap.Map(**default_params)

    def update_map(self, **kwargs):
        """Update map with user-provided zoom, height, and width."""
        valid_params = ['zoom', 'height', 'width']
        update_params = {k: v for k, v in kwargs.items() if k in valid_params}

        if update_params:
            # Update map attributes
            for key, value in update_params.items():
                if key == 'zoom':
                    self.map.zoom = value
                elif key == 'height':
                    self.map.height = value
                elif key == 'width':
                    self.map.width = value

            # Reinitialize map with updated parameters
            current_params = {
                'draw_control': self.map.draw_control,
                'measure_control': self.map.measure_control,
                'fullscreen_control': self.map.fullscreen_control,
                'attribution_control': self.map.attribution_control,
                'zoom': self.map.zoom,
                'height': self.map.height,
                'width': self.map.width
            }
            self.map = leafmap.Map(**current_params)

        return self.map

    def add_basemap(self, basemap='OpenStreetMap'):
        """Add a basemap to the map."""
        self.map.add_basemap(basemap)
        return self.map

    def add_legend(self, title="Legend", labels=None, colors=None):
        """Add a legend to the map."""
        if labels is None or colors is None:
            raise ValueError("Both labels and colors must be provided")
        if len(labels) != len(colors):
            raise ValueError("Number of labels must match number of colors")

        legend_dict = dict(zip(labels, colors))
        self.map.add_legend(title=title, legend_dict=legend_dict)
        return self.map

    def add_grids(self, show_north_arrow=True):
        """Add grids and optionally a north arrow to the map."""
        # Add grid lines
        self.map.add_graticule(interval=1, style={'color': '#000000', 'weight': 0.5})

        # Add north arrow if specified
        if show_north_arrow:
            # Create a custom HTML for north arrow
            north_arrow_html = '''
            <div style="
                background-color: white;
                border: 2px solid black;
                width: 40px;
                height: 60px;
                position: absolute;
                bottom: 30px;
                right: 10px;
                z-index: 1000;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                border-radius: 4px;">
                <div style="
                    width: 0;
                    height: 0;
                    border-left: 10px solid transparent;
                    border-right: 10px solid transparent;
                    border-bottom: 20px solid black;">
                </div>
                <span style="font-size: 14px; font-weight: bold;">N</span>
            </div>
            '''
            self.map.add_html(north_arrow_html)

        return self.map

    def add_gdf(self, gdf, **kwargs):
        """Add a GeoDataFrame to the map."""
        self.map.add_gdf(gdf, **kwargs)
        return self.map




