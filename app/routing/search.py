"""Route search on the road graph: one engine, two algorithms.

A* is Dijkstra with a heuristic: an estimate of the cost that remains to reach
the destination. With an estimate that is always zero, A* behaves exactly like
Dijkstra. So both share one engine, and the two public functions only choose the
estimate:

- ``dijkstra`` uses zero.
- ``a_star`` uses the straight-line distance (haversine) to the destination.

The straight-line distance never overestimates, because the cost of an edge is
at least its length and the graph keeps every length at or above the straight
line between its nodes. It is also consistent, so a node taken out of the heap
already has its best cost and never has to be visited again.

The cost of crossing an edge is ``length x (1 + k x damage)``.
"""

import math
from collections.abc import Callable

from app.geo import haversine_m
from app.routing.errors import NoRouteError
from app.routing.result import Algorithm, RouteResult, RouteStep
from app.structures.graph import Edge, RoadGraph, check_damage_factor
from app.structures.min_heap import IndexedMinHeap
from app.structures.stack import Stack

Heuristic = Callable[[int], float]
"""Estimate of the cost that remains from a node (by internal index) to the destination."""


def dijkstra(graph: RoadGraph, source: int, target: int, k: float = 1.0) -> RouteResult:
    """Find the cheapest route from source to target (internal node indexes)."""
    return _search(graph, source, target, k, lambda _node: 0.0, "dijkstra")


def a_star(graph: RoadGraph, source: int, target: int, k: float = 1.0) -> RouteResult:
    """Find the cheapest route from source to target, guided by the straight-line distance."""
    graph.node_id(source)  # raises GraphError if the index is outside the graph
    goal_latitude, goal_longitude = graph.coordinates(target)

    def straight_line_to_target(node: int) -> float:
        latitude, longitude = graph.coordinates(node)
        return haversine_m(latitude, longitude, goal_latitude, goal_longitude)

    return _search(graph, source, target, k, straight_line_to_target, "a_star")


def _search(
    graph: RoadGraph,
    source: int,
    target: int,
    k: float,
    heuristic: Heuristic,
    algorithm: Algorithm,
) -> RouteResult:
    graph.node_id(source)  # raises GraphError if the index is outside the graph
    graph.node_id(target)
    check_damage_factor(k)

    size = graph.node_count
    best_cost = [math.inf] * size
    """Lowest cost found so far from the source to each node."""
    came_by: list[tuple[int, Edge] | None] = [None] * size
    """For each node, the previous node and the edge used to reach it."""
    done = [False] * size
    heap = IndexedMinHeap(size)
    explored = 0

    best_cost[source] = 0.0
    heap.push(source, heuristic(source))
    while not heap.is_empty():
        node, _ = heap.pop_min()
        explored += 1
        done[node] = True
        if node == target:
            return _build_result(graph, came_by, source, target, k, algorithm, explored)
        for edge in graph.neighbors(node):
            neighbor = edge.target
            if done[neighbor]:
                continue
            cost = best_cost[node] + edge.cost(k)
            if cost < best_cost[neighbor]:
                best_cost[neighbor] = cost
                came_by[neighbor] = (node, edge)
                priority = cost + heuristic(neighbor)
                if heap.contains(neighbor):
                    heap.decrease_key(neighbor, priority)
                else:
                    heap.push(neighbor, priority)

    raise NoRouteError(source, target)


def _build_result(
    graph: RoadGraph,
    came_by: list[tuple[int, Edge] | None],
    source: int,
    target: int,
    k: float,
    algorithm: Algorithm,
    explored: int,
) -> RouteResult:
    """Walk the path backwards from the target, then use stacks to put it in travel order."""
    steps_on_stack: Stack[RouteStep] = Stack()
    nodes_on_stack: Stack[int] = Stack()
    node = target
    nodes_on_stack.push(node)
    while node != source:
        link = came_by[node]
        assert link is not None, "every node on the path has a previous node"
        previous, edge = link
        steps_on_stack.push(
            RouteStep(
                edge.segment_id, edge.reversed, edge.length_m, edge.damage_score, edge.cost(k)
            )
        )
        nodes_on_stack.push(previous)
        node = previous

    steps = tuple(steps_on_stack.pop() for _ in range(len(steps_on_stack)))
    node_indexes = tuple(nodes_on_stack.pop() for _ in range(len(nodes_on_stack)))
    return RouteResult(
        algorithm=algorithm,
        steps=steps,
        node_indexes=node_indexes,
        total_length_m=sum(step.length_m for step in steps),
        total_cost=sum(step.cost for step in steps),
        explored_nodes=explored,
    )
