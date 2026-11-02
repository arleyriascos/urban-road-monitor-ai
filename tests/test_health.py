from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings
from app.main import create_app


def make_client() -> TestClient:
    settings = Settings(
        _env_file=None,
        app_env="test",
        internal_token="a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4",
    )
    return TestClient(create_app(settings))


def test_health_reports_the_service_is_running() -> None:
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "urban-road-monitor-ai",
        "version": __version__,
    }


def test_health_never_exposes_the_token() -> None:
    response = make_client().get("/health")

    assert "a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4a1b2c3d4" not in response.text


def test_health_is_listed_in_the_api_documentation() -> None:
    response = make_client().get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
