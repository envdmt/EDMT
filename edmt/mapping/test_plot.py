import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx

def plot_df(df, column=None, ax=None,legend=None):
    "Plot based on the `geometry` column of a GeoPandas dataframe"
    df = df.copy()
    df = df.to_crs(epsg=4326)  # WGS 84

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 8))

    df.plot(
        ax=ax,
        # cmap=cmap,
        alpha=0.5, 
        edgecolor='black',
        column=column, 
        # categorical=True,
        legend=legend,
        legend_kwds={
        'loc': 'lower right',
        'bbox_to_anchor': (1, 0),  # Controls position (x, y)
        'frameon': True,  # Optional: add a frame around the legend
        'colorbar': False
        },
    )
    cx.add_basemap(ax, crs=df.crs, source=cx.providers.CartoDB.Positron)


def plot_shape(shape, ax=None):
    df = gpd.GeoDataFrame({'geometry': [shape]}, crs='EPSG:4326')
    plot_df(df, ax=ax)