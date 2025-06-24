from edmt import (
    analysis, 
    base, 
    contrib, 
    conversion, 
    mapping, 
    models, 
    plotting
    )

import importlib.metadata

ASCII = r"""\
 ___ ___  __  __ _____ 
| __|   \|  \/  |_   _|
| _|| |) | |\/| | | |  
|___|___/|_|  |_| |_|  
"""

__initialized = False

# Package version
__version__ = importlib.metadata.version("edmt")

def init(silent=False, force=False):
    """
    Initializes the environment with EDMT-specific customizations.

    Parameters
    ----------
    silent : bool, optional
        Suppresses console output (default is False).
    force : bool, optional
        Forces re-initialization even if already initialized (default is False).
    """
    global __initialized
    if __initialized and not force:
        if not silent:
            print("EDMT already initialized.")
        return
    
    import pandas as pd
    import warnings

    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option("plotting.backend", "matplotlib")

    warnings.filterwarnings(
        "ignore",
        message="The 'shapely.geos' module is deprecated",
        category=DeprecationWarning,
        module='geopandas._compat'
    )
    warnings.filterwarnings("ignore", message="Unable to import Axes3D")

    __initialized = True
    if not silent:
        print(ASCII)
        print("EDMT initialized successfully.")

__all__ = ["analysis", "base", "contrib", "init", "conversion", "mapping", "models", "plotting"]
