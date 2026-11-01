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

import pytest

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
