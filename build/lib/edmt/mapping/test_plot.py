import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import contextily as cx

from ..contrib.utils import clean_vars

import seaborn as sns

# class Mapping():

#     def plot_df(df, column=None, title=None,ax=None, legend=True):
#         """
#         Plot a GeoDataFrame with optional dynamic column-based styling and a categorical legend.
        
#         Parameters:
#         - df: GeoDataFrame to plot.
#         - column: Column name for coloring the geometries. Assumes categorical data.
#         - ax: Matplotlib axis object. If None, a new figure is created.
#         - legend: Whether to include a legend in the plot.
#         """
#         df = df.copy()
#         df = df.to_crs(epsg=4326)  # Ensure WGS 84 

#         # Create plot
#         if ax is None:
#             _, ax = plt.subplots(figsize=(10, 10))

#         plot_args = {
#             "ax":ax,
#             "alpha": 0.6,
#             "edgecolor": "black",
#             "column": column,
#             "legend": legend,
#             "legend_kwds": {
#                 "loc": "lower right",
#                 "bbox_to_anchor": (1, 0),
#                 "frameon": True,
#                 "title": column,
#             },
#         }

#         df.plot(**plot_args)

#         # Add basemap
        

#         if title is None:
#             # Format axis
#             ax.set_axis_off()
#             return cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)
        
#         else:
#             # Format axis
#             ax.set_axis_off()
#             ax.set_title(f"{title}", fontsize=14)

#             return cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)


#     def plot_gdf(df, column=None, title=None,ax=None, legend=True):
#         """
#         Plot a GeoDataFrame with optional dynamic column-based styling and a categorical legend.
        
#         Parameters:
#         - df: GeoDataFrame to plot.
#         - column: Column name for coloring the geometries. Assumes categorical data.
#         - ax: Matplotlib axis object. If None, a new figure is created.
#         - legend: Whether to include a legend in the plot.
#         """
#         df = df.copy()
#         df = df.to_crs(epsg=4326)  # Ensure WGS 84 

#         # Create plot
#         if ax is None:
#             _, ax = plt.subplots(figsize=(10, 10))

#         plot_args = {
#             "ax":ax,
#             "alpha": 0.6,
#             "edgecolor": "black",
#             "column": column,
#             "legend": legend,
#             "legend_kwds": {
#                 "loc": "lower right",
#                 "bbox_to_anchor": (1, 0),
#                 "frameon": True,
#                 "title": column,
#             },
#         }

#         df.plot(**plot_args)

#         # Add basemap
        

#         if title is None:
#             # Format axis
#             ax.set_axis_off()
#             return cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)
        
#         else:
#             # Format axis
#             ax.set_axis_off()
#             ax.set_title(f"{title}", fontsize=14)

#             return cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)




class Mapping:

    @staticmethod
    def gplot(df, column=None, title=None, ax=None, legend=True):
        """
        Plot a GeoDataFrame with optional dynamic column-based styling and a categorical legend.
        """
        df = df.copy()
        df = df.to_crs(epsg=4326)  # Ensure WGS 84 

        # Create plot
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 10))

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
        }

        df.plot(**plot_args)

        # Add basemap
        ax.set_axis_off()
        if title:
            ax.set_title(title, fontsize=14)

        cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)

        return ax


    @staticmethod
    def plot(df):
        """
        Plot a GeoDataFrame with optional dynamic column-based styling and a categorical legend.
        """
        df = df.copy()
        df = df.to_crs(epsg=4326)  # Ensure WGS 84 

        # Create plot
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 10))

        return ax
