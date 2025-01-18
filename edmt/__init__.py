import importlib.metadata

# Submodule imports
from . import analysis, base, contrib, conversion, mapping, models, plotting

# Package version
__version__ = importlib.metadata.version("edmt")

# ASCII art for EDMT banner
ASCII = r"""
  ______ _____  __  __ _______ 
 |  ____|  __ \|  \/  |__   __|
 | |__  | |  | | \  / |  | |   
 |  __| | |  | | |\/| |  | |   
 | |____| |__| | |  | |  | |   
 |______|_____/|_|  |_|  |_|   
"""

# Initialization state
__initialized = False


def init(silent: bool = False, force: bool = False):
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

    # Check if already initialized
    if __initialized and not force:
        if not silent:
            print("EDMT is already initialized.")
        return

    # Set the initialization flag
    __initialized = True

    # Display ASCII art if not silent
    if not silent:
        print(ASCII)
        print(f"EDMT initialized successfully. Version: {__version__}")
