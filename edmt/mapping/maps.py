import contextily as cx
from edmt.contrib.utils import clean_vars

class Mapping:
    def __init__(self):
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

    def gplot(self, df):
        """
        Plot the GeoDataFrame and store the axis object.
        """
        df = self.process_df(df)
        self.ax = df.plot(alpha=0.7)
        cx.add_basemap(self.ax, source=cx.providers.CartoDB.Positron)
        self.ax.set_axis_off()
        return self

    def add_title(self, title):
        if self.ax:
            self.ax.set_title(title)
        return self

    def add_grids(self, linewidth: float = 0.5, alpha: float = 0.7):
        """
        Add a grid to the plot with customizable styling.

        Parameters:
            linewidth (float): The width of the grid lines. Default is 0.5.
            alpha (float): The transparency of the grid lines. Default is 0.7.

        Returns:
            Mapping: The instance of the class, for method chaining.
        """
        if self.ax:
            args = {
                "visible": True,
                "linestyle": "--",
                "linewidth": linewidth,
                "alpha": alpha,
            }
            args = {key: value for key, value in args.items() if value is not None}
            self.ax.grid(**args)
        return self

    def add_labels(self):
        if self.ax:
            self.ax.tick_params(labeltop=False, labelright=False, labelsize=8, pad=-20)
        return self

    def add_legend(self):
        if self.ax:
            self.ax.legend(loc="lower right", bbox_to_anchor=(1, 0), frameon=True)
            self.ax.set_axis_off()
        return self

    def add_basemap(self, source=cx.providers.CartoDB.Positron):
        if self.ax:
            cx.add_basemap(self.ax, source=source)
            self.ax.set_axis_off()
        return self
