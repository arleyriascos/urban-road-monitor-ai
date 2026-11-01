"""Geographic helpers shared by the graph, the search and the click locator."""

import math

EARTH_RADIUS_M = 6_371_008.8
"""Mean Earth radius in meters. It is the same value the backend uses, so both
services measure the same distance between two points."""


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two (latitude, longitude) points in degrees.

    It is the length of the shortest path over the Earth's surface, so no street
    between the two points can be shorter. A* uses it as its heuristic.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))
