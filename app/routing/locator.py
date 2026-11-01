"""Turn a clicked map point into the nearest intersection of the road network.

Only the nodes of the main component count: the largest group of nodes joined
by streets, found with the union-find. Loose pieces of road, like a parking lot
that touches no other street, can never be part of a route, so a click near one
is moved to the real network or rejected.

The search is linear, and it is fast enough for the 7,613 nodes of Pasto. In
Stage 4 the Quadtree replaces it without changing this interface.
"""

import math
from dataclasses import dataclass

from app.geo import haversine_m
from app.routing.errors import InvalidPointError, OutsideNetworkError
from app.structures.graph import GraphError, RoadGraph

DEFAULT_MAX_DISTANCE_M = 200.0
"""How far a click may be from the network. It is adjusted when testing on real data."""


@dataclass(frozen=True, slots=True)
class SnappedNode:
    """The intersection chosen for a clicked point."""

    index: int
    """Internal index of the node in the graph."""
    distance_m: float
    """Distance in meters from the clicked point to the node."""


class NodeLocator:
    """Finds the nearest intersection of the main road network."""

    def __init__(self, graph: RoadGraph, max_distance_m: float = DEFAULT_MAX_DISTANCE_M) -> None:
        if not (math.isfinite(max_distance_m) and max_distance_m > 0):
            raise GraphError(f"max_distance_m must be a number > 0, got {max_distance_m}")
        if graph.node_count == 0:
            raise GraphError("the graph has no nodes")
        self._graph = graph
        self._max_distance_m = max_distance_m
        components = graph.components()
        main_root = components.find(components.largest_root())
        self._candidates: tuple[int, ...] = tuple(
            index for index in range(graph.node_count) if components.find(index) == main_root
        )
        """Nodes of the main component, in ascending index order."""

    @property
    def max_distance_m(self) -> float:
        return self._max_distance_m

    @property
    def main_component_size(self) -> int:
        """Number of nodes in the main component."""
        return len(self._candidates)

    def snap(self, latitude: float, longitude: float) -> SnappedNode:
        """Return the nearest node of the main component to a point.

        On a tie, the node with the lowest index wins. Raises OutsideNetworkError
        if the nearest node is farther than the limit.
        """
        if not (math.isfinite(latitude) and -90 <= latitude <= 90):
            raise InvalidPointError(f"invalid latitude: {latitude}")
        if not (math.isfinite(longitude) and -180 <= longitude <= 180):
            raise InvalidPointError(f"invalid longitude: {longitude}")

        best_index = -1
        best_distance = math.inf
        for index in self._candidates:
            node_latitude, node_longitude = self._graph.coordinates(index)
            distance = haversine_m(latitude, longitude, node_latitude, node_longitude)
            if distance < best_distance:
                best_index, best_distance = index, distance

        if best_distance > self._max_distance_m:
            raise OutsideNetworkError(latitude, longitude, best_distance, self._max_distance_m)
        return SnappedNode(best_index, best_distance)
