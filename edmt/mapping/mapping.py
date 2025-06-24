import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import contextily as cx
from pyproj import CRS

from edmt.contrib.utils import clean_vars

class Mapping:
    def __init__(self):
        # Initialize any necessary attributes
        pass

#     @staticmethod
#     def gplot(df, column=None, title=None, legend=True, fill=None, grids=None, **additional_args):
#         df = df.copy()
#         df = df.to_crs(epsg=4326)

#         ax = plt.subplots(figsize=(10, 10))
#         plot_args = {
#             "ax": ax,
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
#             "facecolor": fill,
#         }
#         plot_args = clean_vars(additional_args, **plot_args)
#         df.plot(**plot_args)
#         cx.add_basemap(ax, crs=df.crs, source=cx.providers.OpenStreetMap.Mapnik)
#         return ax

# class Mapping:

#     def __init__(self):
#         # Initialize any necessary attributes
#         pass

#     @staticmethod
#     def gplot(df, column=None, title=None, ax=None, legend=True, fill=None,grids=None, **additional_args):
#         # print(f"Plot started at: {datetime.now()}")
#         # start_time = time.time()

#         df = df.copy()
#         df = df.to_crs(epsg=4326)  # Ensure WGS 84

#         # Create plot
#         if ax is None:
#             _, ax = plt.subplots(figsize=(10, 10))

#         # Default plot arguments
#         plot_args = {
#             "ax": ax,
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
#             "facecolor" : fill
#         }

#         # Title
#         if title:
#             ax.set_title(title, fontsize=14)

#         # Add grids
#         if grids:
#             ax.grid(visible=True, linestyle="--", linewidth=0.5, alpha=0.7)

#         # Clean and merge additional arguments
#         plot_args = clean_vars(additional_args, **plot_args)

#         # Plot the GeoDataFrame
#         df.plot(**plot_args)

#         # Add a frame around the map
#         for spine in ax.spines.values():
#             spine.set_edgecolor("black")
#             spine.set_linewidth(1.5)

#         # Add basemap
#         cx.add_basemap(ax, crs=df.crs, source=cx.providers.OpenStreetMap.Mapnik)

#         # end_time = time.time()
#         # execution_time = end_time - start_time
#         # print(f"Execution time: {execution_time:.2f} seconds.")
#         return ax

#     # def gplot(df, column=None, title=None, legend=True, fill=None, grids=None):

#     #     df = df.copy()
#     #     if df.crs is None:
#     #         raise ValueError("Input GeoDataFrame must have a CRS defined.")
#     #     if df.crs != CRS.from_epsg(4326):
#     #         df = df.to_crs(epsg=4326)  # Ensure WGS 84

#     #     ax=ax

#     #     # Default plot arguments
#     #     plot_args = {
#     #         "ax": ax,
#     #         "alpha": 0.6,
#     #         "edgecolor": "black",
#     #     }

#     #     # Add column-specific arguments if a column is provided
#     #     if column:
#     #         plot_args["column"] = column
#     #         plot_args["legend"] = legend
#     #         plot_args["legend_kwds"] = {
#     #             "loc": "lower right",
#     #             "bbox_to_anchor": (1, 0),
#     #             "frameon": True,
#     #             "title": column,
#     #         }

#     #     # Add fill color
#     #     if fill:
#     #         plot_args["color"] = fill

#     #     # Set title
#     #     if title:
#     #         ax.set_title(title, fontsize=14)

#     #     # Add grids if specified
#     #     if grids:
#     #         ax.grid(visible=True, linestyle="--", linewidth=0.5, alpha=0.7)

#     #     # Plot the GeoDataFrame
#     #     df.plot(**plot_args)

#     #     # Add a frame around the map
#     #     for spine in ax.spines.values():
#     #         spine.set_edgecolor("black")
#     #         spine.set_linewidth(1.5)

#     #     # Add basemap
#     #     cx.add_basemap(ax, crs=df.crs, source=cx.providers.OpenStreetMap.Mapnik)
#     #     return ax
    
#     @staticmethod
#     def TileLayer(self, df):

#         "list of base layers to use"

#         """
#         Add names, opacity, 

#         addl_args()

#         Use clean var to
#         """

#     @staticmethod
#     def title(df):
#         """
#         Plot a GeoDataFrame with optional dynamic column-based styling and a categorical legend.
#         """
#         df = df.copy()
#         df = df.to_crs(epsg=4326)  # Ensure WGS 84 

#         # Create plot
#         if ax is None:
#             _, ax = plt.subplots(figsize=(10, 10))

#         return ax
    
#     @staticmethod
#     def legend(df):

#         return df
    
#     @staticmethod
#     def scale_bar(df):

#         return df
    
#     @staticmethod
#     def add_table(df):

#         return df
    
#     @staticmethod
#     def html(df):

#         return df
    
#     @staticmethod
#     def png(df):

#         return df
    
#     @staticmethod
#     def legend(df):

#         return df