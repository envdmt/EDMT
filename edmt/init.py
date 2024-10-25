ASCII = """\
  ______ _____  __  __ _______ 
 |  ____|  __ \|  \/  |__   __|
 | |__  | |  | | \  / |  | |   
 |  __| | |  | | |\/| |  | |   
 | |____| |__| | |  | |  | |   
 |______|_____/|_|  |_|  |_|   
                               
                      
"""

__initialized = False


# def init(silent=False, force=False):
#     """
#     Initializes the environment with Library-specific customizations.

#     Parameters
#     ----------
#     silent : bool, optional
#         Removes console output
#     force : bool, optional
#         Ignores `__initialized`

#     """

#     print(ASCII)



def init(silent=False, force=False):
    """
    Initializes the environment with ecoscope-specific customizations.

    Parameters
    ----------
    silent : bool, optional
        Removes console output
    force : bool, optional
        Ignores `__initialized`

    """

    global __initialized
    if __initialized and not force:
        if not silent:
            print("EDMT already initialized.")
        return

    import pandas as pd

    pd.options.plotting.backend = "plotly"

    # Enable copy-on-write for pandas. It will be the default in pandas 3.0.
    pd.options.mode.copy_on_write = True

    from tqdm.auto import tqdm

    tqdm.pandas()

    import warnings

    from shapely.errors import ShapelyDeprecationWarning

    warnings.filterwarnings(action="ignore", category=ShapelyDeprecationWarning)
    warnings.filterwarnings(action="ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=".*initial implementation of EDMT.*")

    import plotly as pio

    pio.templates.default = "seaborn"

    __initialized = True
    if not silent:
        print(ASCII)



__all__ = ["base.py", "load.py"]