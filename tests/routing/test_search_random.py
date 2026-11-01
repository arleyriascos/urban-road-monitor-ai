"""Random street grids to check Dijkstra and A* against independent references.

- Dijkstra is compared with Bellman-Ford, a slow but obvious algorithm that
  relaxes every edge until nothing improves.
- A* is compared with Dijkstra: both must find routes of the same cost.
- Every route is also checked edge by edge against the graph.

The seeds are fixed, so every run performs the same checks.
"""

import math
import random
from collections.abc import Callable

import pytest

from app.geo import haversine_m
from app.routing.errors import NoRouteError
from app.routing.result import RouteResult
from app.routing.search import a_star, dijkstra
from app.structures.graph import RoadGraph

GridFactory = Callable[[int, int, int], RoadGraph]

ROWS, COLS = 8, 8
SOURCES_PER_GRID = 8
TARGETS_PER_SOURCE = 8


def bellman_ford(graph: RoadGraph, source: int, k: float) -> list[float]:
    """Cheapest cost from the source to every node, by relaxing all edges repeatedly."""
    cost = [math.inf] * graph.node_count
    cost[source] = 0.0
    for _ in range(graph.node_count - 1):
        improved = False
        for node in range(graph.node_count):
            if cost[node] == math.inf:
                continue
            for edge in graph.neighbors(node):
                candidate = cost[node] + edge.cost(k)
                if candidate < cost[edge.target]:
                    cost[edge.target] = candidate
                    improved = True
        if not improved:
            break
    return cost


def assert_route_matches_the_graph(
    graph: RoadGraph, result: RouteResult, source: int, target: int, k: float
) -> None:
    """Each step must be a real edge of the graph between consecutive nodes."""
    nodes = result.node_indexes
    assert nodes[0] == source
    assert nodes[-1] == target
    assert len(result.steps) == len(nodes) - 1
    for start, end, step in zip(nodes[:-1], nodes[1:], result.steps, strict=True):
        edge = next(
            e
            for e in graph.neighbors(start)
            if e.target == end and e.segment_id == step.segment_id and e.reversed == step.reversed
        )
        assert step.length_m == edge.length_m
        assert step.cost == edge.cost(k)
    assert result.total_cost == pytest.approx(sum(s.cost for s in result.steps), rel=1e-12)
    assert result.total_length_m == pytest.approx(sum(s.length_m for s in result.steps), rel=1e-12)


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_both_algorithms_match_bellman_ford(make_grid: GridFactory, seed: int) -> None:
    graph = make_grid(ROWS, COLS, seed)
    rng = random.Random(seed)

    for k in (0.0, 1.0, 3.0):
        for source in rng.sample(range(graph.node_count), SOURCES_PER_GRID):
            reference = bellman_ford(graph, source, k)
            for target in rng.sample(range(graph.node_count), TARGETS_PER_SOURCE):
                for search in (dijkstra, a_star):
                    if math.isinf(reference[target]):
                        with pytest.raises(NoRouteError):
                            search(graph, source, target, k)
                        continue
                    result = search(graph, source, target, k)
                    assert result.total_cost == pytest.approx(reference[target], rel=1e-9)
                    assert_route_matches_the_graph(graph, result, source, target, k)


@pytest.mark.parametrize("seed", [1, 2, 4])
def test_these_grids_have_one_way_streets_that_block_some_routes(
    make_grid: GridFactory, seed: int
) -> None:
    graph = make_grid(ROWS, COLS, seed)

    unreachable = sum(
        math.isinf(cost)
        for source in range(graph.node_count)
        for cost in bellman_ford(graph, source, 0.0)
    )

    # Without these seeds the comparison above would never exercise NoRouteError.
    assert unreachable > 0


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_every_edge_costs_at_least_the_straight_line_between_its_nodes(
    make_grid: GridFactory, seed: int
) -> None:
    graph = make_grid(ROWS, COLS, seed)

    for node in range(graph.node_count):
        for edge in graph.neighbors(node):
            straight = haversine_m(*graph.coordinates(node), *graph.coordinates(edge.target))
            for k in (0.0, 1.0, 3.0):
                assert edge.cost(k) >= straight


def test_a_star_explores_fewer_nodes_than_dijkstra(make_grid: GridFactory) -> None:
    graph = make_grid(12, 12, 7)
    rng = random.Random(7)
    dijkstra_explored = 0
    a_star_explored = 0

    for _ in range(150):
        source, target = rng.sample(range(graph.node_count), 2)
        try:
            slow = dijkstra(graph, source, target, 0.0)
        except NoRouteError:
            continue
        fast = a_star(graph, source, target, 0.0)
        assert fast.total_cost == pytest.approx(slow.total_cost, rel=1e-9)
        dijkstra_explored += slow.explored_nodes
        a_star_explored += fast.explored_nodes

    assert 0 < a_star_explored < dijkstra_explored
