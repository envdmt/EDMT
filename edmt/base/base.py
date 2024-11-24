from ..conversion.gen_uuid import *
from . import  version


"""
Example 

import edmt
edmt.__version__

"""

__version__ = version.get_versions()["version"]