from datetime import UTC, datetime, timedelta

import pytest

from app.clustering.contract import ClusterRequest
from app.clustering.models import Severity
from app.clustering.service import ClusterService
from app.config import Settings
from app.errors import ApiError
from app.graph.client import GraphDownloadError
from app.graph.payload import GraphPayload
from app.graph.store import GraphStore, build_loaded_graph

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
STEP = 0.00001  # about 1.1 meters of latitude


def detection(ident: int, lat: float, lon: float, **changes: object) -> dict[str, object]:
    return {
        "id": ident,
        "latitude": lat,
        "longitude": lon,
        "severity": "moderado",
        "confidence": 0.5,
        "detectedAt": NOW.isoformat(),
        **changes,
    }


def request(detections: list[dict[str, object]], **extra: object) -> ClusterRequest:
    return ClusterRequest.model_validate(
        {"detections": detections, "asOf": NOW.isoformat(), **extra}
    )


@pytest.fixture
def service(sample_payload: GraphPayload) -> ClusterService:
    store = GraphStore(lambda: sample_payload, lambda p: build_loaded_graph(p, 200.0))
    return ClusterService(store, Settings(_env_file=None, app_env="test"))


def test_no_detections_give_no_clusters(service: ClusterService) -> None:
    response = service.cluster(request([]))

    assert response.clusters == []
    assert (response.detection_count, response.cluster_count) == (0, 0)


def test_repeated_sightings_make_a_confirmed_pothole_and_a_lone_one_is_not(
    service: ClusterService,
) -> None:
    response = service.cluster(
        request(
            [
                detection(1, 1.3, -77.4),
                detection(2, 1.3 + STEP, -77.4),
                detection(3, 1.35, -77.45),
            ]
        )
    )

    assert response.detection_count == 3
    assert response.cluster_count == 2
    assert response.confirmed_count == 1
    assert response.clusters[0].detection_ids == [1, 2]
    assert response.clusters[0].status == "confirmed"
    assert response.clusters[0].confidence == pytest.approx(0.75)
    assert response.clusters[1].status == "unconfirmed"


def test_without_a_graph_version_the_potholes_have_no_segment(service: ClusterService) -> None:
    response = service.cluster(request([detection(1, 1.21405, -77.2805)]))

    assert response.graph_version is None
    assert response.placed_count == 0
    assert response.clusters[0].segment_id is None


def test_with_a_graph_version_each_pothole_gets_its_segment(service: ClusterService) -> None:
    response = service.cluster(request([detection(1, 1.21405, -77.2805)], graphVersion="sample-v1"))

    pothole = response.clusters[0]
    assert response.graph_version == "sample-v1"
    assert response.placed_count == 1
    assert pothole.segment_id == 1001
    assert pothole.segment_fraction == pytest.approx(0.5, abs=0.05)
    assert pothole.segment_distance_m is not None and pothole.segment_distance_m < 1.0


def test_a_pothole_far_from_every_street_is_clustered_but_not_placed(
    service: ClusterService,
) -> None:
    response = service.cluster(request([detection(1, 1.2, -77.4)], graphVersion="sample-v1"))

    assert response.cluster_count == 1
    assert response.placed_count == 0


def test_if_the_graph_cannot_be_loaded_the_potholes_are_still_clustered() -> None:
    def broken() -> GraphPayload:
        raise GraphDownloadError("backend down", retryable=True)

    store = GraphStore(broken, lambda p: build_loaded_graph(p, 200.0))
    service = ClusterService(store, Settings(_env_file=None, app_env="test"))

    response = service.cluster(request([detection(1, 1.2, -77.3)], graphVersion="sample-v1"))

    assert response.cluster_count == 1
    assert response.graph_version is None
    assert response.clusters[0].segment_id is None


def test_the_settings_of_the_request_override_the_defaults(service: ClusterService) -> None:
    far = [detection(1, 1.3, -77.4), detection(2, 1.3 + 20 * STEP, -77.4)]  # about 22 m

    assert service.cluster(request(far)).cluster_count == 2
    wide = service.cluster(request(far, epsM=30))
    assert wide.cluster_count == 1
    assert wide.eps_m == 30
    assert service.cluster(request(far, minPoints=1)).confirmed_count == 2


def test_the_confidence_fades_with_the_time_before_as_of(service: ClusterService) -> None:
    old = detection(
        1, 1.3, -77.4, confidence=0.8, detectedAt=(NOW - timedelta(days=30)).isoformat()
    )

    response = service.cluster(request([old]))

    assert response.clusters[0].confidence == pytest.approx(0.4)
    assert response.clusters[0].severity is Severity.MODERADO


def test_as_of_defaults_to_now(service: ClusterService) -> None:
    body = ClusterRequest.model_validate({"detections": []})

    response = service.cluster(body)

    assert abs((datetime.now(UTC) - response.as_of).total_seconds()) < 5


def test_too_many_detections_are_refused() -> None:
    settings = Settings(_env_file=None, app_env="test", cluster_max_detections=2)
    service = ClusterService(GraphStore(lambda: None, lambda p: None), settings)  # type: ignore[arg-type, return-value]
    body = request([detection(i, 1.3 + i * 0.01, -77.4) for i in range(3)])

    with pytest.raises(ApiError) as caught:
        service.cluster(body)

    assert caught.value.status_code == 422
    assert caught.value.code == "TOO_MANY_DETECTIONS"
    assert caught.value.details == {"received": 3, "limit": 2}


def test_repeated_ids_are_refused(service: ClusterService) -> None:
    with pytest.raises(ApiError) as caught:
        service.cluster(request([detection(1, 1.3, -77.4), detection(1, 1.4, -77.4)]))

    assert (caught.value.status_code, caught.value.code) == (422, "DUPLICATE_DETECTION_ID")
