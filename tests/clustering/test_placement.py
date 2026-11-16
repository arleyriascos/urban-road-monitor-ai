from datetime import UTC, datetime

import pytest

from app.clustering.clusters import Cluster, ClusterStatus
from app.clustering.models import Severity
from app.clustering.placement import place_clusters
from app.routing.segment_locator import SegmentLocator

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
STEP = 0.00001  # about 1.1 meters of latitude

# Two streets 100 m long, 220 m apart.
STREETS = {
    1: [(1.2, -77.3), (1.2 + 90 * STEP, -77.3)],
    2: [(1.2, -77.298), (1.2 + 90 * STEP, -77.298)],
}


def pothole(lat: float, lon: float, ident: int = 1) -> Cluster:
    return Cluster((ident,), lat, lon, Severity.LEVE, 0.5, ClusterStatus.UNCONFIRMED, NOW, NOW)


def test_a_pothole_near_a_street_is_placed_on_it() -> None:
    placed = place_clusters([pothole(1.2 + 45 * STEP, -77.30002)], SegmentLocator(STREETS))

    assert placed[0].segment_id == 1
    assert placed[0].distance_m == pytest.approx(2.2, abs=0.1)
    assert placed[0].fraction == pytest.approx(0.5, abs=0.01)


def test_each_pothole_goes_to_its_own_street_and_keeps_the_order() -> None:
    potholes = [pothole(1.2 + 10 * STEP, -77.298, 1), pothole(1.2 + 80 * STEP, -77.3, 2)]

    placed = place_clusters(potholes, SegmentLocator(STREETS))

    assert [p.segment_id for p in placed] == [2, 1]
    assert [p.cluster for p in placed] == potholes


def test_a_pothole_far_from_every_street_has_no_segment() -> None:
    placed = place_clusters([pothole(1.2 + 45 * STEP, -77.299)], SegmentLocator(STREETS))

    assert (placed[0].segment_id, placed[0].distance_m, placed[0].fraction) == (None, None, None)


def test_the_distance_limit_can_be_changed() -> None:
    far = pothole(1.2 + 45 * STEP, -77.30030)  # about 33 m from the street

    assert place_clusters([far], SegmentLocator(STREETS))[0].segment_id is None
    assert place_clusters([far], SegmentLocator(STREETS), max_distance_m=40.0)[0].segment_id == 1


def test_without_a_locator_no_pothole_has_a_segment() -> None:
    placed = place_clusters([pothole(1.2, -77.3)], None)

    assert placed[0].segment_id is None


def test_no_potholes_give_nothing() -> None:
    assert place_clusters([], SegmentLocator(STREETS)) == []
