import pytest

from app.graph.payload import GraphPayload
from app.graph.store import build_loaded_graph


def test_the_loaded_graph_finds_the_segment_of_a_place(sample_payload: GraphPayload) -> None:
    loaded = build_loaded_graph(sample_payload, 200.0)
    assert loaded.segment_locator is not None

    # Halfway along segment 1001, between nodes 101 and 102.
    match = loaded.segment_locator.locate(1.21405, -77.2805, 20.0)

    assert match is not None
    assert match.segment_id == 1001
    assert match.distance_m < 1.0
    assert match.fraction == pytest.approx(0.5, abs=0.05)


def test_a_street_without_geometry_is_a_straight_line_between_its_nodes(
    sample_payload: GraphPayload,
) -> None:
    loaded = build_loaded_graph(sample_payload, 200.0)
    assert loaded.segment_locator is not None

    match = loaded.segment_locator.locate(1.2200, -77.2700, 5.0)

    assert match is not None
    assert match.segment_id == 1005
    assert match.fraction == pytest.approx(0.0, abs=0.01)


def test_the_geometry_of_a_street_is_used_when_it_comes(sample_payload: GraphPayload) -> None:
    # Segment 1001 goes from node 101 to node 102, but bends north on the way.
    bent = [(1.2140, -77.2810), (1.2160, -77.2805), (1.2141, -77.2800)]
    segments = [
        s.model_copy(update={"geometry": bent}) if s.id == 1001 else s
        for s in sample_payload.segments
    ]
    loaded = build_loaded_graph(sample_payload.model_copy(update={"segments": segments}), 200.0)
    assert loaded.segment_locator is not None

    on_the_bend = loaded.segment_locator.locate(1.2160, -77.2805, 5.0)
    on_the_straight_line = loaded.segment_locator.locate(1.21405, -77.2805, 5.0)

    assert on_the_bend is not None and on_the_bend.segment_id == 1001
    assert on_the_straight_line is None


def test_a_graph_without_segments_has_no_segment_locator(sample_payload: GraphPayload) -> None:
    empty = sample_payload.model_copy(update={"segments": []})

    assert build_loaded_graph(empty, 200.0).segment_locator is None
