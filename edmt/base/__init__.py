from .base import (
    AirdataBaseClass,
    ExtractCSV
)

__all__ = [
    "AirdataBaseClass",
    "ExtractCSV"
]


for _name in __all__:
    globals()[_name].__module__ = __name__


