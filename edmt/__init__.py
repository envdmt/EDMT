from .base.base import *
from .base import version

__version__ = version.get_versions()["version"]

ASCII = """\
  ______ _____  __  __ _______ 
 |  ____|  __ \|  \/  |__   __|
 | |__  | |  | | \  / |  | |   
 |  __| | |  | | |\/| |  | |   
 | |____| |__| | |  | |  | |   
 |______|_____/|_|  |_|  |_|   
                               
                               
"""

__initialized = False


def init(silent=False, force=False):
    """
    Initializes the environment with edmt-specific customizations.

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


    __initialized = True
    if not silent:
        print(ASCII)

__all__ = ["analysis", "base", "contrib", "conversion","mapping", "models","plotting"]