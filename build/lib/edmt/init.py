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
    Initializes the environment with Library-specific customizations.

    Parameters
    ----------
    silent : bool, optional
        Removes console output
    force : bool, optional
        Ignores `__initialized`

    """

    print(ASCII)