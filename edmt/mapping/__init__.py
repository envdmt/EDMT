from .carto import (
    make_qr
)

__all__ = [
    "make_qr"
]

for _name in __all__:
    globals()[_name].__module__ = __name__

    