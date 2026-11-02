"""Road networks written by hand, shared by the tests of graphs and routes.

Sample network:

      104
       ^  Carrera 25 (one-way, north)
       |
101 -- 102 -- 103      Calle 18 (two-way); 102-103 has a moderate pothole
               ^
               |  Carrera 24 (one-way, north; oneway=-1 in OpenStreetMap,
              105           already flipped by the backend importer)

201 -- 202             parking lot that touches no other street
"""

import random
from collections.abc import Callable

import pytest

from app.geo import haversine_m
from app.graph.payload import GraphNodeIn, GraphPayload, GraphSegmentIn
from app.structures.graph import RoadGraph

NODES = [
    (101, 1.2140, -77.2810),
    (102, 1.2141, -77.2800),
    (103, 1.2142, -77.2790),
    (104, 1.2150, -77.2800),
    (105, 1.2130, -77.2790),
    (201, 1.2200, -77.2700),
    (202, 1.2201, -77.2699),
]

# (segment_id, from_node_id, to_node_id, length_m, damage_score, is_oneway)
# Every length is at least the straight-line distance between its nodes.
SEGMENTS = [
    (1001, 101, 102, 112.0, 0.0, False),
    (1002, 102, 103, 112.0, 2.0, False),
    (1003, 102, 104, 101.0, 0.0, True),
    (1004, 105, 103, 134.0, 0.5, True),
    (1005, 201, 202, 16.0, 0.0, False),
]


@pytest.fixture
def sample_graph() -> RoadGraph:
    graph = RoadGraph()
    for node in NODES:
        graph.add_node(*node)
    for segment in SEGMENTS:
        graph.add_segment(*segment)
    return graph


@pytest.fixture
def sample_payload() -> GraphPayload:
    """The sample network as GET /internal/graph of the backend sends it."""
    return GraphPayload(
        version="sample-v1",
        nodes=[GraphNodeIn(id=node_id, latitude=lat, longitude=lon) for node_id, lat, lon in NODES],
        segments=[
            GraphSegmentIn(
                id=segment_id,
                from_node_id=start,
                to_node_id=end,
                length_m=length,
                damage_score=damage,
                is_oneway=oneway,
            )
            for segment_id, start, end, length, damage, oneway in SEGMENTS
        ],
    )


@pytest.fixture
def diamond_graph() -> RoadGraph:
    """Two ways from 301 to 302: a short damaged road and a longer clean detour.

         303
        /   \\
      301 -- 302      301-302: 224 m, damage 0.3; detour 301-303-302: 2 x 158 m, no damage

    With k = 0 the short road wins (224 m against 316 m). With k = 1 it still wins
    (224 x 1.3 = 291 m). With k = 3 it costs 224 x 1.9 = 426 m, so the detour wins.
    """
    graph = RoadGraph()
    graph.add_node(301, 1.2000, -77.2800)
    graph.add_node(302, 1.2000, -77.2780)
    graph.add_node(303, 1.2010, -77.2790)
    graph.add_segment(3001, 301, 302, 224.0, 0.3, False)
    graph.add_segment(3002, 301, 303, 158.0, 0.0, False)
    graph.add_segment(3003, 303, 302, 158.0, 0.0, False)
    return graph


GridFactory = Callable[[int, int, int], RoadGraph]


@pytest.fixture
def make_grid() -> GridFactory:
    """Build a rows x cols street grid with random lengths, damage and one-way streets.

    Blocks are about 100 m apart. The same seed always gives the same grid, so the
    random tests are repeatable. About a third of the streets are one-way, in a
    random direction, so some pairs of nodes have no route.
    """

    def build(rows: int, cols: int, seed: int) -> RoadGraph:
        rng = random.Random(seed)
        graph = RoadGraph()
        for row in range(rows):
            for col in range(cols):
                graph.add_node(row * cols + col, 1.2000 + row * 0.0009, -77.2800 + col * 0.0009)

        segment_id = 0
        for row in range(rows):
            for col in range(cols):
                for next_row, next_col in ((row, col + 1), (row + 1, col)):
                    if next_row >= rows or next_col >= cols:
                        continue
                    a = row * cols + col
                    b = next_row * cols + next_col
                    straight = haversine_m(*graph.coordinates(a), *graph.coordinates(b))
                    length = straight * rng.uniform(1.0, 1.3)
                    damage = rng.choice([0.0, 0.0, 0.2, 1.0, 3.0])
                    oneway = rng.random() < 0.33
                    if oneway and rng.random() < 0.5:
                        a, b = b, a
                    graph.add_segment(segment_id, a, b, length, damage, oneway)
                    segment_id += 1
        return graph

    return build
