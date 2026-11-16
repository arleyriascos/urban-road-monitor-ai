"""POST /clusters over HTTP: the contract the backend relies on."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.graph.payload import GraphPayload
from app.graph.store import GraphStore, build_loaded_graph
from app.main import create_app

TOKEN = "0123456789abcdef" * 4
AUTH = {"Authorization": f"Bearer {TOKEN}"}
STEP = 0.00001  # about 1.1 meters of latitude


def seen(ident: int, lat: float, lon: float, **changes: Any) -> dict[str, Any]:
    return {
        "id": ident,
        "latitude": lat,
        "longitude": lon,
        "severity": "grave",
        "confidence": 0.6,
        "detectedAt": "2026-11-16T12:00:00Z",
        **changes,
    }


@pytest.fixture
def client(sample_payload: GraphPayload) -> TestClient:
    settings = Settings(_env_file=None, app_env="test", internal_token=TOKEN)
    store = GraphStore(lambda: sample_payload, lambda p: build_loaded_graph(p, 200.0))
    return TestClient(create_app(settings, store, warm_up=False))


def post(client: TestClient, body: dict[str, Any]) -> Any:
    return client.post("/clusters", json=body, headers=AUTH)


def test_answers_the_potholes_in_camel_case(client: TestClient) -> None:
    response = post(
        client,
        {
            "detections": [seen(1, 1.21405, -77.2805), seen(2, 1.21405 + STEP, -77.2805)],
            "graphVersion": "sample-v1",
            "asOf": "2026-11-16T12:00:00Z",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["graphVersion"] == "sample-v1"
    assert body["detectionCount"] == 2
    assert body["clusterCount"] == 1
    assert body["confirmedCount"] == 1
    assert body["placedCount"] == 1
    pothole = body["clusters"][0]
    assert pothole["detectionIds"] == [1, 2]
    assert pothole["count"] == 2
    assert pothole["severity"] == "grave"
    assert pothole["status"] == "confirmed"
    assert pothole["confidence"] == pytest.approx(0.84)
    assert pothole["segmentId"] == 1001
    assert pothole["firstDetectedAt"] == "2026-11-16T12:00:00Z"


def test_the_answer_is_never_cached(client: TestClient) -> None:
    response = post(client, {"detections": []})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_works_without_a_graph_version(client: TestClient) -> None:
    body = post(client, {"detections": [seen(1, 1.3, -77.4)]}).json()

    assert body["graphVersion"] is None
    assert body["clusters"][0]["segmentId"] is None
    assert body["clusters"][0]["status"] == "unconfirmed"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"detections": [seen(1, 91.0, -77.4)]},
        {"detections": [seen(1, 1.3, -77.4, confidence=2)]},
        {"detections": [seen(1, 1.3, -77.4, severity="critico")]},
        {"detections": [seen(1, 1.3, -77.4, detectedAt="2026-11-16T12:00:00")]},
        {"detections": [], "epsM": 0},
    ],
)
def test_an_invalid_request_is_a_422_with_the_project_error_shape(
    client: TestClient, body: dict[str, Any]
) -> None:
    response = post(client, body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_repeated_detection_ids_are_a_422(client: TestClient) -> None:
    response = post(client, {"detections": [seen(1, 1.3, -77.4), seen(1, 1.4, -77.4)]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DUPLICATE_DETECTION_ID"


def test_too_many_detections_are_a_422_that_says_the_limit(
    sample_payload: GraphPayload,
) -> None:
    settings = Settings(
        _env_file=None, app_env="test", internal_token=TOKEN, cluster_max_detections=2
    )
    store = GraphStore(lambda: sample_payload, lambda p: build_loaded_graph(p, 200.0))
    client = TestClient(create_app(settings, store, warm_up=False))

    response = post(client, {"detections": [seen(i, 1.3 + i * 0.01, -77.4) for i in range(3)]})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TOO_MANY_DETECTIONS"
    assert response.json()["error"]["details"] == {"received": 3, "limit": 2}


def test_the_endpoint_appears_in_the_openapi_description(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "post" in paths["/clusters"]
