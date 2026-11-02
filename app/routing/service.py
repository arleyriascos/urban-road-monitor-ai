"""Answers a route request with the graph in memory.

It snaps both clicked points to the main road network, runs A* or Dijkstra, and turns
the internal indexes into the ids of the database. Lengths are rounded to centimeters
and costs to four decimals, the precision of route_requests in the database.
"""

import time

from app.errors import ApiError
from app.graph.store import GraphStore, GraphUnavailableError, LoadedGraph
from app.routing.contract import Point, RouteRequest, RouteResponse, RouteStepOut, SnappedPoint
from app.routing.errors import NoRouteError, OutsideNetworkError
from app.routing.locator import SnappedNode
from app.routing.search import a_star, dijkstra


class RouteService:
    def __init__(self, store: GraphStore) -> None:
        self._store = store

    def find_route(self, request: RouteRequest) -> RouteResponse:
        try:
            loaded = self._store.get(request.graph_version)
        except GraphUnavailableError as error:
            raise ApiError(
                503,
                "GRAPH_UNAVAILABLE",
                "The road graph is not available right now; try again in a moment",
            ) from error

        origin = self._snap(loaded, request.origin, "origin")
        destination = self._snap(loaded, request.destination, "destination")
        search = a_star if request.algorithm == "astar" else dijkstra
        graph = loaded.graph

        started = time.perf_counter()
        try:
            result = search(graph, origin.index, destination.index, request.k)
        except NoRouteError as error:
            raise ApiError(
                404,
                "NO_ROUTE",
                "There is no route between these points that respects one-way streets",
                details={
                    "originNodeId": graph.node_id(origin.index),
                    "destinationNodeId": graph.node_id(destination.index),
                },
            ) from error
        computation_ms = round((time.perf_counter() - started) * 1000)

        return RouteResponse(
            algorithm=request.algorithm,
            graph_version=loaded.version,
            origin=self._snapped_point(loaded, origin),
            destination=self._snapped_point(loaded, destination),
            total_length_m=round(result.total_length_m, 2),
            total_cost=round(result.total_cost, 4),
            explored_nodes=result.explored_nodes,
            computation_ms=computation_ms,
            node_ids=[graph.node_id(index) for index in result.node_indexes],
            steps=[
                RouteStepOut(
                    segment_id=step.segment_id,
                    reversed=step.reversed,
                    length_m=round(step.length_m, 2),
                    damage_score=step.damage_score,
                    cost=round(step.cost, 4),
                )
                for step in result.steps
            ],
        )

    @staticmethod
    def _snap(loaded: LoadedGraph, point: Point, label: str) -> SnappedNode:
        try:
            return loaded.locator.snap(point.latitude, point.longitude)
        except OutsideNetworkError as error:
            raise ApiError(
                422,
                "OUTSIDE_NETWORK",
                f"The {label} is {error.distance_m:.0f} m from the road network; "
                f"the limit is {error.max_distance_m:.0f} m",
                details={
                    "point": label,
                    "distanceM": round(error.distance_m, 2),
                    "maxDistanceM": error.max_distance_m,
                },
            ) from error

    @staticmethod
    def _snapped_point(loaded: LoadedGraph, snapped: SnappedNode) -> SnappedPoint:
        latitude, longitude = loaded.graph.coordinates(snapped.index)
        return SnappedPoint(
            node_id=loaded.graph.node_id(snapped.index),
            latitude=latitude,
            longitude=longitude,
            distance_m=round(snapped.distance_m, 2),
        )
