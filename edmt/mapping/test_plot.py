import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import contextily as cx

def plot_df(df, column=None, ax=None, legend=None, title=None):
    """
    Plot the geometry column of a GeoPandas dataframe using interactive map visualization.

    Parameters:
        df (GeoDataFrame): The GeoPandas dataframe to plot.
        column (str, optional): Column name to color the plot. Defaults to None.
        ax (matplotlib.axes.Axes, optional): Matplotlib axis for the plot. Defaults to None.
        legend (bool, optional): Whether to display the legend. Defaults to None.
        title (str, optional): Title for the plot. Defaults to None.

    Returns:
        folium.Map: Interactive map visualization of the dataframe.
    """
    # Ensure the input is not modified
    df = df.copy()

    # Reproject to WGS 84 (EPSG:4326)
    df = df.to_crs(epsg=4326)

    # Create a new axis if none is provided
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    # Generate the interactive map using GeoPandas' explore
    return df.explore(
        ax=ax,
        alpha=0.5, 
        edgecolor='black',
        column=column, 
        legend=legend,
        legend_kwds={
            'loc': 'lower right',
            'bbox_to_anchor': (1, 0),
            'frameon': True,
        },
        title=title
    )

#     cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)


# def plot_shape(shape, ax=None):
#     df = gpd.GeoDataFrame({'geometry': [shape]}, crs='EPSG:4326')
#     plot_df(df, ax=ax)




def plot_gdf(df, column=None, title=None,ax=None, legend=True):
    """
    Plot a GeoDataFrame with optional dynamic column-based styling and a categorical legend.
    
    Parameters:
    - df: GeoDataFrame to plot.
    - column: Column name for coloring the geometries. Assumes categorical data.
    - ax: Matplotlib axis object. If None, a new figure is created.
    - legend: Whether to include a legend in the plot.
    """
    df = df.copy()
    df = df.to_crs(epsg=4326)  # Ensure WGS 84 

    # Create plot
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 10))

    plot_args = {
        "ax":ax,
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
    

    if title is None:
        # Format axis
        ax.set_axis_off()
        return cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)
    
    else:
        # Format axis
        ax.set_axis_off()
        ax.set_title(f"{title}", fontsize=14)

        return cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)


