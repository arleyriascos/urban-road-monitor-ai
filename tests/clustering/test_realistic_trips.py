"""Detections that look like the real ones: many trips pass the same potholes, each time
seen from a slightly different place because of the GPS error of a phone."""

import random
import time
from datetime import UTC, datetime, timedelta

from app.clustering.clusters import ClusterStatus, build_clusters
from app.clustering.models import Detection, Severity

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
METER = 0.000009  # degrees of latitude in one meter


def trips_over(
    potholes: list[tuple[float, float]], trips: int, rng: random.Random, first_id: int = 1
) -> list[Detection]:
    detections: list[Detection] = []
    ident = first_id
    for trip in range(trips):
        for lat, lon in potholes:
            if rng.random() < 0.8:  # the camera misses some
                detections.append(
                    Detection(
                        ident,
                        lat + rng.gauss(0, 1.5 * METER),
                        lon + rng.gauss(0, 1.5 * METER),
                        rng.choice([Severity.MODERADO, Severity.GRAVE]),
                        rng.uniform(0.4, 0.9),
                        NOW - timedelta(days=trip, minutes=ident % 60),
                    )
                )
                ident += 1
    return detections


def test_many_trips_over_few_potholes_give_one_confirmed_cluster_per_pothole() -> None:
    rng = random.Random(41)
    potholes = [(1.2 + i * 0.001, -77.3 + (i % 3) * 0.001) for i in range(6)]  # >100 m apart

    clusters = build_clusters(trips_over(potholes, 25, rng), NOW)

    assert len(clusters) == 6
    assert all(c.status is ClusterStatus.CONFIRMED for c in clusters)
    assert all(c.count >= 10 for c in clusters)
    assert all(c.confidence > 0.99 for c in clusters)


def test_each_center_lands_within_a_meter_of_the_real_pothole() -> None:
    rng = random.Random(42)
    potholes = [(1.2 + i * 0.001, -77.3) for i in range(4)]

    clusters = build_clusters(trips_over(potholes, 30, rng), NOW)

    for lat, lon in potholes:
        nearest = min(clusters, key=lambda c: abs(c.latitude - lat) + abs(c.longitude - lon))
        assert abs(nearest.latitude - lat) < 1.0 * METER
        assert abs(nearest.longitude - lon) < 1.0 * METER


def test_a_pothole_seen_once_waits_unconfirmed_until_another_trip_sees_it() -> None:
    new = (1.2005, -77.3)
    first_trip = [Detection(1, *new, Severity.LEVE, 0.6, NOW)]
    second_trip = [Detection(2, new[0] + 2 * METER, new[1], Severity.LEVE, 0.7, NOW)]

    alone = build_clusters(first_trip, NOW)
    together = build_clusters(first_trip + second_trip, NOW)

    assert [c.status for c in alone] == [ClusterStatus.UNCONFIRMED]
    assert [c.status for c in together] == [ClusterStatus.CONFIRMED]
    assert together[0].confidence > alone[0].confidence


def test_twenty_thousand_detections_are_clustered_in_a_few_seconds() -> None:
    rng = random.Random(44)
    potholes = [(1.18 + rng.uniform(0, 0.08), -77.33 + rng.uniform(0, 0.08)) for _ in range(1500)]
    detections = trips_over(potholes, 17, rng)
    assert len(detections) > 15_000

    started = time.perf_counter()
    clusters = build_clusters(detections, NOW)
    seconds = time.perf_counter() - started

    assert len(clusters) >= 1000
    assert seconds < 10.0  # a generous limit: it takes about a second on a normal computer
