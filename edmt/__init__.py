from ._edmt import list_functions
import importlib

ASCII = r"""
 ___ ___  __  __ _____ 
| __|   \|  \/  |_   _|
| _|| |) | |\/| | | |  
|___|___/|_|  |_| |_|  
"""

__initialized = False

# Package version
__version__ = importlib.metadata.version("edmt")



_MODULES = {
    "analysis",
    "base",
    "contrib",
    "conversion",
    "mapping",
    "models",
    "plotting",
    "workflow",
}

def __getattr__(name):
    if name in _MODULES:
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



def init(silent=False, force=False):
    """
    Initializes the environment with EDMT-specific customizations.

    Parameters:
    ------------
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
    
    pd.set_option("display.max_columns", None)
    pd.options.plotting.backend = "plotly"
    pd.options.mode.copy_on_write = True

    from tqdm.auto import tqdm

    tqdm.pandas()

    import warnings

    from shapely.errors import ShapelyDeprecationWarning

    warnings.filterwarnings(action="ignore", category=ShapelyDeprecationWarning)
    warnings.filterwarnings(action="ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=".*initial implementation of Parquet.*")
    warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

    import plotly.io as pio  # type: ignore[import-untyped]

    pio.templates.default = "seaborn"

    __initialized = True
    if not silent:
        print(ASCII)
        print("EDMT initialized successfully.")


__all__ = [
    "analysis", 
    "base", 
    "contrib", 
    "init", 
    "conversion", 
    "mapping", 
    "models", 
    "plotting",
    "list_functions",
    "workflow"
]