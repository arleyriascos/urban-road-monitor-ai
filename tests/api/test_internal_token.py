"""Only the backend, with the shared token, can ask for routes."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.graph.payload import GraphPayload
from app.graph.store import GraphStore, build_loaded_graph
from app.main import create_app

TOKEN = "0123456789abcdef" * 4
BODY = {
    "origin": {"latitude": 1.21401, "longitude": -77.28101},
    "destination": {"latitude": 1.21421, "longitude": -77.27901},
    "graphVersion": "sample-v1",
}
UNAUTHORIZED = {"error": {"code": "UNAUTHORIZED", "message": "A valid internal token is required"}}


def make_client(payload: GraphPayload, token: str | None) -> TestClient:
    settings = Settings(_env_file=None, app_env="test", internal_token=token)
    store = GraphStore(lambda: payload, lambda p: build_loaded_graph(p, 200.0))
    return TestClient(create_app(settings, store, warm_up=False))


def test_the_right_token_gets_the_route(sample_payload: GraphPayload) -> None:
    response = make_client(sample_payload, TOKEN).post(
        "/routes", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert response.status_code == 200


def test_accepts_the_scheme_name_in_any_case(sample_payload: GraphPayload) -> None:
    response = make_client(sample_payload, TOKEN).post(
        "/routes", json=BODY, headers={"Authorization": f"bearer {TOKEN}"}
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": f"Bearer {'f' * 64}"},
        {"Authorization": "Bearer short"},
        {"Authorization": TOKEN},
        {"Authorization": f"Basic {TOKEN}"},
        {"Authorization": "Bearer "},
    ],
    ids=["no-header", "wrong", "other-length", "no-scheme", "basic", "empty"],
)
def test_answers_401_with_one_message(
    sample_payload: GraphPayload, headers: dict[str, str]
) -> None:
    response = make_client(sample_payload, TOKEN).post("/routes", json=BODY, headers=headers)

    assert response.status_code == 401
    assert response.json() == UNAUTHORIZED
    assert response.headers["www-authenticate"] == 'Bearer realm="internal"'
    assert response.headers["cache-control"] == "no-store"


def test_checks_the_token_before_reading_the_body(sample_payload: GraphPayload) -> None:
    invalid: dict[str, Any] = {"origin": "not a point"}

    response = make_client(sample_payload, TOKEN).post("/routes", json=invalid)

    assert response.status_code == 401


def test_the_endpoint_does_not_exist_without_a_configured_token(
    sample_payload: GraphPayload,
) -> None:
    client = make_client(sample_payload, None)

    turned_off = client.post("/routes", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"})
    unknown = client.post("/unknown", json=BODY)

    assert turned_off.status_code == 404
    assert turned_off.json() == {
        "error": {"code": "NOT_FOUND", "message": "Route POST /routes does not exist"}
    }
    assert unknown.json()["error"]["code"] == "NOT_FOUND"


def test_never_sends_the_token_back(sample_payload: GraphPayload) -> None:
    client = make_client(sample_payload, TOKEN)

    wrong = client.post("/routes", json=BODY, headers={"Authorization": f"Bearer {TOKEN[:40]}"})
    right = client.post("/routes", json=BODY, headers={"Authorization": f"Bearer {TOKEN}"})

    assert TOKEN[:40] not in wrong.text
    assert TOKEN not in right.text
