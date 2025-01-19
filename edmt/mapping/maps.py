maps_ = ["Mapping"]


import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import contextily as cx
from pyproj import CRS

from edmt.contrib.utils import clean_vars

class Mapping:
    def __init__(self):
        # Initialize any necessary attributes
        self.default_crs = 4326  # Default CRS (WGS 84)
        self.df_cache = None  # Optional: Cache the last processed GeoDataFrame

    def process_df(self, df):
        """
        Process the GeoDataFrame for plotting.
        This can include caching, CRS transformation, or other preprocessing.
        """
        # Cache the original GeoDataFrame
        self.df_cache = df.copy()
        # Reproject to the default CRS
        return self.df_cache.to_crs(epsg=self.default_crs)

    def gplot(self, df, column=None, title=None, legend=True, fill=None, grids=None, **additional_args):
        df = self.process_df(df)

        fig, ax = plt.subplots(figsize=(10, 10))
        plot_args = {
            "ax": ax,
            "alpha": 0.6,
            "edgecolor": "black",
            "column": column,
            "legend": legend,
            "legend_kwds": {
                "loc": "lower right",
                "bbox_to_anchor": (1, 0),
                "frameon": True,
                "title": column,
            },
            "facecolor": fill,
        }

        plot_args = clean_vars(additional_args, **plot_args)
        df.plot(**plot_args)
        cx.add_basemap(ax, crs=df.crs, source=cx.providers.OpenStreetMap.Mapnik)

        if title:
            ax.set_title(title, fontsize=14)

        if grids:
            ax.grid(visible=True, linestyle="--", linewidth=0.5, alpha=0.7)

        return ax
