import contextily as cx
from edmt.contrib.utils import clean_vars
# from geopandas import plotting as plot

class Mapping:
    def __init__(self, static=False,  **kwargs):
        self.height = kwargs.get("height")
        self.width = kwargs.get("width")
        super().__init__(**kwargs)

    def process_df(self, df):
        """
        Process the GeoDataFrame for plotting.
        Includes caching and CRS transformation.
        """
        self.df_cache = df.copy()
        return self.df_cache#.to_crs(epsg=self.default_crs)


    def figure(self, height: int, width: int, **kwargs):
        """
        Update the figure dimensions.
        """
        self.height = height  
        self.width = width
        kwargs["height"] = height
        kwargs["width"] = width
        return kwargs


    def gplot(self, df,column:str=None,**kwargs):
        """
        Plot the GeoDataFrame and store the axis object.
        """
        df = self.process_df(df)
        self.ax = df.plot(alpha=0.7,column=column,**kwargs)
        cx.add_basemap(self.ax, source=cx.providers.CartoDB.Positron)
        self.ax.set_axis_off()
        return self