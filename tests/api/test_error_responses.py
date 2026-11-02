"""Every error answers with the same JSON shape as the backend."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, app_env="test")))


def test_an_unknown_route_answers_a_json_404() -> None:
    response = make_client().get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Route GET /does-not-exist does not exist"}
    }


def test_a_wrong_method_answers_a_json_405() -> None:
    response = make_client().post("/health")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["allow"]


def test_the_health_check_still_works() -> None:
    assert make_client().get("/health").status_code == 200
