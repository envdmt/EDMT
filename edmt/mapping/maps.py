import contextily as cx
from edmt.contrib.utils import clean_vars
# from geopandas import plotting as plot

class Mapping:
    def __init__(self,**kwargs):
        self.default_crs = 4326
        self.df_cache = None
        self.ax = None

    def process_df(self, df):
        """
        Process the GeoDataFrame for plotting.
        Includes caching and CRS transformation.
        """
        self.df_cache = df.copy()
        return self.df_cache.to_crs(epsg=self.default_crs)

    def get_crs(self):
        return self.default_crs

    def set_crs(self, crs):
        self.default_crs = crs

    def gplot(self, df,column:str=None,**kwargs):
        """
        Plot the GeoDataFrame and store the axis object.
        """
        df = self.process_df(df)
        self.ax = df.plot(alpha=0.7,column=column)
        cx.add_basemap(self.ax, source=cx.providers.CartoDB.Positron)
        self.ax.set_axis_off()
        return self

    def figure(self, width, height):
        if self.ax:
            self.ax.set_figwidth(width)
            self.ax.set_figheight(height)
        return self

        # usage
        # figure(12, 6)

    def add_colorbar(self):
        if self.ax:
            self.ax.get_figure().colorbar
        return self

    def add_axis(self):
        if self.ax:
            self.ax.set_axis_on()
        return self

    def add_title(self, title):
        if self.ax:
            self.ax.set_title(title)
        return self

    def add_grids(self):
        if self.ax:
            self.ax.grid(visible=True, linestyle="--", linewidth=0.5, alpha=0.7)
        return self

    def add_labels(self):
        if self.ax:
            self.ax.tick_params(labeltop=False, labelright=False, labelsize=8, pad=-20)
        return self

    

    def add_basemap(self, providers=None,tile=None):
        if providers and tile:
            source = f"cx.providers.{providers}.{tile}"
            if self.ax:
                cx.add_basemap(self.ax, source=source)
                self.ax.set_axis_off()
            return self
