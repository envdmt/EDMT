from .drones import (
    Airdata,
    _flight_polyline,
    get_flight_routes,
    airPoint,
    airLine,
    airSegment
)

__all__ = [
    "Airdata",
    "_flight_polyline",
    "get_flight_routes",
    "airPoint",
    "airLine",
    "airSegment"
]

for _name in __all__:
    globals()[_name].__module__ = __name__

    