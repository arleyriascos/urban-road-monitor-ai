"""POST /routes over HTTP: the contract the backend relies on."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.graph.client import GraphDownloadError
from app.graph.payload import GraphPayload
from app.graph.store import GraphStore, LoadedGraph, build_loaded_graph
from app.main import create_app

TOKEN = "0123456789abcdef" * 4
AUTH = {"Authorization": f"Bearer {TOKEN}"}

# Clicks a few meters from the intersections of the sample network.
NEAR = {
    101: {"latitude": 1.21401, "longitude": -77.28101},
    102: {"latitude": 1.21412, "longitude": -77.27999},
    103: {"latitude": 1.21421, "longitude": -77.27901},
    105: {"latitude": 1.21299, "longitude": -77.27899},
}
FAR_AWAY = {"latitude": 1.2500, "longitude": -77.2500}


def build(payload: GraphPayload) -> LoadedGraph:
    return build_loaded_graph(payload, 200.0)


def client_for(store: GraphStore) -> TestClient:
    settings = Settings(_env_file=None, app_env="test", internal_token=TOKEN)
    return TestClient(create_app(settings, store, warm_up=False))


@pytest.fixture
def client(sample_payload: GraphPayload) -> TestClient:
    return client_for(GraphStore(lambda: sample_payload, build))


def route(
    client: TestClient,
    origin: int | dict[str, float],
    destination: int | dict[str, float],
    **extra: Any,
) -> Any:
    body = {
        "origin": NEAR[origin] if isinstance(origin, int) else origin,
        "destination": NEAR[destination] if isinstance(destination, int) else destination,
        "graphVersion": "sample-v1",
        **extra,
    }
    return client.post("/routes", json=body, headers=AUTH)


def test_answers_the_route_with_database_ids(client: TestClient) -> None:
    response = route(client, 101, 103, k=0)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["algorithm"] == "astar"
    assert body["graphVersion"] == "sample-v1"
    assert body["nodeIds"] == [101, 102, 103]
    assert [step["segmentId"] for step in body["steps"]] == [1001, 1002]
    assert [step["reversed"] for step in body["steps"]] == [False, False]
    assert body["totalLengthM"] == 224.0
    assert body["totalCost"] == 224.0
    assert body["exploredNodes"] >= 3
    assert isinstance(body["computationMs"], int)


def test_uses_camel_case_names_like_the_rest_of_the_project(client: TestClient) -> None:
    body = route(client, 101, 103).json()

    assert set(body) == {
        "algorithm",
        "graphVersion",
        "origin",
        "destination",
        "totalLengthM",
        "totalCost",
        "exploredNodes",
        "computationMs",
        "nodeIds",
        "steps",
    }
    assert set(body["origin"]) == {"nodeId", "latitude", "longitude", "distanceM"}
    assert set(body["steps"][0]) == {"segmentId", "reversed", "lengthM", "damageScore", "cost"}


def test_reports_where_each_click_was_snapped(client: TestClient) -> None:
    body = route(client, 101, 103).json()

    assert body["origin"]["nodeId"] == 101
    assert (body["origin"]["latitude"], body["origin"]["longitude"]) == (1.214, -77.281)
    assert 0 < body["origin"]["distanceM"] < 5
    assert body["destination"]["nodeId"] == 103


@pytest.mark.parametrize(("k", "cost"), [(0, 224.0), (1, 448.0), (3, 896.0)])
def test_the_damage_factor_changes_the_cost(client: TestClient, k: float, cost: float) -> None:
    assert route(client, 101, 103, k=k).json()["totalCost"] == cost


def test_k_is_1_when_the_backend_does_not_send_it(client: TestClient) -> None:
    assert route(client, 101, 103).json()["totalCost"] == 448.0


def test_dijkstra_finds_the_same_cost_as_astar(client: TestClient) -> None:
    astar = route(client, 105, 101, algorithm="astar").json()
    dijkstra = route(client, 105, 101, algorithm="dijkstra").json()

    assert dijkstra["algorithm"] == "dijkstra"
    assert dijkstra["totalCost"] == astar["totalCost"]
    assert dijkstra["nodeIds"] == astar["nodeIds"]


def test_steps_come_in_travel_order_with_their_direction(client: TestClient) -> None:
    body = route(client, 105, 101).json()

    assert body["nodeIds"] == [105, 103, 102, 101]
    assert [step["segmentId"] for step in body["steps"]] == [1004, 1002, 1001]
    assert [step["reversed"] for step in body["steps"]] == [False, True, True]


def test_the_same_origin_and_destination_give_a_route_without_steps(client: TestClient) -> None:
    body = route(client, 102, 102).json()

    assert body["steps"] == []
    assert body["nodeIds"] == [102]
    assert (body["totalLengthM"], body["totalCost"]) == (0.0, 0.0)


def test_no_route_when_one_way_streets_block_the_way(client: TestClient) -> None:
    response = route(client, 101, 105)

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "NO_ROUTE",
        "message": "There is no route between these points that respects one-way streets",
        "details": {"originNodeId": 101, "destinationNodeId": 105},
    }


@pytest.mark.parametrize("which", ["origin", "destination"])
def test_a_click_far_from_the_network_says_which_one_and_how_far(
    client: TestClient, which: str
) -> None:
    ends: dict[str, Any] = {"origin": 101, "destination": 103}
    ends[which] = FAR_AWAY

    response = route(client, ends["origin"], ends["destination"])

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "OUTSIDE_NETWORK"
    assert error["details"]["point"] == which
    assert error["details"]["distanceM"] > 200
    assert error["details"]["maxDistanceM"] == 200.0
    assert which in error["message"]


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"origin": {"latitude": 91, "longitude": -77.28}}, "origin.latitude"),
        ({"k": -1}, "k"),
        ({"algorithm": "a_star"}, "algorithm"),
        ({"graphVersion": ""}, "graphVersion"),
        ({"unexpected": True}, "unexpected"),
    ],
)
def test_rejects_an_invalid_request(client: TestClient, change: dict[str, Any], field: str) -> None:
    body: dict[str, Any] = {
        "origin": NEAR[101],
        "destination": NEAR[103],
        "graphVersion": "sample-v1",
        **change,
    }

    response = client.post("/routes", json=body, headers=AUTH)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "INVALID_REQUEST"
    assert field in [problem["field"] for problem in error["details"]["errors"]]


def test_rejects_a_request_without_graph_version(client: TestClient) -> None:
    response = client.post(
        "/routes", json={"origin": NEAR[101], "destination": NEAR[103]}, headers=AUTH
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_answers_503_when_no_graph_can_be_loaded() -> None:
    def failing_download() -> GraphPayload:
        raise GraphDownloadError("could not connect to the backend at x", retryable=True)

    response = route(client_for(GraphStore(failing_download, build)), 101, 103)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GRAPH_UNAVAILABLE"


def test_reloads_the_graph_when_the_backend_sends_a_new_version(
    sample_payload: GraphPayload,
) -> None:
    worse = sample_payload.model_copy(
        update={
            "version": "sample-v2",
            "segments": [
                s.model_copy(update={"damage_score": 4.0}) if s.id == 1002 else s
                for s in sample_payload.segments
            ],
        }
    )
    replies = [sample_payload, worse]
    store = GraphStore(lambda: replies.pop(0), build, cooldown_s=0)
    client = client_for(store)

    before = route(client, 101, 103, k=1).json()
    after = route(client, 101, 103, k=1, graphVersion="sample-v2").json()

    assert (before["graphVersion"], before["totalCost"]) == ("sample-v1", 448.0)
    assert (after["graphVersion"], after["totalCost"]) == ("sample-v2", 672.0)


def test_reports_the_version_actually_used_within_the_cooldown(client: TestClient) -> None:
    route(client, 101, 103)  # loads sample-v1

    body = route(client, 101, 103, graphVersion="something-newer").json()

    # The backend asked for another version; it must not cache this answer under it.
    assert body["graphVersion"] == "sample-v1"


def test_is_documented_with_its_errors(client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"]["/routes"]["post"]

    assert set(operation["responses"]) >= {"200", "401", "404", "422", "503"}
