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


BoundingBox = tuple[float, float, float, float]
"""A map rectangle: (min_latitude, min_longitude, max_latitude, max_longitude), in degrees."""


def bounding_box(latitude: float, longitude: float, radius_m: float) -> BoundingBox:
    """Smallest latitude and longitude rectangle that holds every point within radius_m.

    The Quadtree uses it to leave out whole areas of the map before it measures any
    distance. Every point whose haversine distance to the center is at most radius_m
    is inside the rectangle, so no point is lost. The reverse is not true: the corners
    of the rectangle are farther than radius_m, so the caller still measures.

    Near a pole the rectangle takes every longitude, because there a small circle
    goes all the way around the Earth.
    """
    if radius_m < 0:
        raise ValueError(f"radius_m must not be negative, got {radius_m}")
    angle = radius_m / EARTH_RADIUS_M
    phi = math.radians(latitude)
    min_lat = max(-90.0, math.degrees(phi - angle))
    max_lat = min(90.0, math.degrees(phi + angle))
    if abs(phi) + angle >= math.pi / 2:
        return (min_lat, -180.0, max_lat, 180.0)
    d_lon = math.degrees(math.asin(math.sin(angle) / math.cos(phi)))
    return (min_lat, longitude - d_lon, max_lat, longitude + d_lon)
