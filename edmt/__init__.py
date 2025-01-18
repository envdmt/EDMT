from .base.__init__ import *
import importlib.metadata

from . import analysis
from . import base
from . import contrib
from . import conversion
from . import mapping
from . import models
from . import plotting

__version__  = importlib.metadata.version("edmt")

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


