"""Errors of the route computation.

Each one carries the data the backend needs to tell the user what happened,
instead of a generic failure.
"""


class RoutingError(Exception):
    """Base class of the errors of the route computation."""


class NoRouteError(RoutingError):
    """The destination cannot be reached from the origin respecting one-way streets."""

    def __init__(self, source: int, target: int) -> None:
        super().__init__(
            f"there is no route from node {source} to node {target} that respects one-way streets"
        )
        self.source = source
        """Internal index of the origin node."""
        self.target = target
        """Internal index of the destination node."""


class OutsideNetworkError(RoutingError):
    """A clicked point is too far from the road network."""

    def __init__(
        self, latitude: float, longitude: float, distance_m: float, max_distance_m: float
    ) -> None:
        super().__init__(
            f"the point ({latitude:.6f}, {longitude:.6f}) is {distance_m:.0f} m from the "
            f"road network; the limit is {max_distance_m:.0f} m"
        )
        self.latitude = latitude
        self.longitude = longitude
        self.distance_m = distance_m
        """Distance in meters to the nearest node of the main road network."""
        self.max_distance_m = max_distance_m


class InvalidPointError(RoutingError, ValueError):
    """A latitude or longitude is not a valid coordinate."""
