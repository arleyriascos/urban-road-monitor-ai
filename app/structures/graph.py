"""Directed road graph stored as an adjacency list.

Each node of ``road_nodes`` gets an internal index from 0 to n - 1, so the
graph, the min-heap and the union-find can work with plain lists. The database
ids only appear when data enters or leaves the graph.
"""

import math


class GraphError(ValueError):
    """Raised when the graph would receive invalid data."""


class RoadGraph:
    """Road network of Pasto: intersections with internal indexes."""

    def __init__(self) -> None:
        self._index_of: dict[int, int] = {}
        """Database node id -> internal index."""
        self._node_ids: list[int] = []
        """Internal index -> database node id."""
        self._latitudes: list[float] = []
        self._longitudes: list[float] = []

    @property
    def node_count(self) -> int:
        return len(self._node_ids)

    def add_node(self, node_id: int, latitude: float, longitude: float) -> int:
        """Add an intersection and return its internal index."""
        if node_id in self._index_of:
            raise GraphError(f"node {node_id} was already added")
        if not (math.isfinite(latitude) and -90 <= latitude <= 90):
            raise GraphError(f"node {node_id} has an invalid latitude: {latitude}")
        if not (math.isfinite(longitude) and -180 <= longitude <= 180):
            raise GraphError(f"node {node_id} has an invalid longitude: {longitude}")
        index = len(self._node_ids)
        self._index_of[node_id] = index
        self._node_ids.append(node_id)
        self._latitudes.append(latitude)
        self._longitudes.append(longitude)
        return index

    def has_node(self, node_id: int) -> bool:
        return node_id in self._index_of

    def index_of(self, node_id: int) -> int:
        """Internal index of a database node id."""
        try:
            return self._index_of[node_id]
        except KeyError:
            raise GraphError(f"node {node_id} is not in the graph") from None

    def node_id(self, index: int) -> int:
        """Database node id of an internal index."""
        self._check_index(index)
        return self._node_ids[index]

    def coordinates(self, index: int) -> tuple[float, float]:
        """Latitude and longitude of a node."""
        self._check_index(index)
        return self._latitudes[index], self._longitudes[index]

    def _check_index(self, index: int) -> None:
        if not 0 <= index < len(self._node_ids):
            raise GraphError(f"index {index} is outside 0..{len(self._node_ids) - 1}")
