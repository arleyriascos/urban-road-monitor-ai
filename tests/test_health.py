from fastapi.testclient import TestClient

from app import __version__
from app.config import Settings
from app.graph.payload import GraphPayload
from app.graph.store import GraphStore, build_loaded_graph
from app.main import create_app

TOKEN = "a1b2c3d4" * 8


def make_client(store: GraphStore | None = None) -> TestClient:
    settings = Settings(_env_file=None, app_env="test", internal_token=TOKEN)
    return TestClient(create_app(settings, store, warm_up=False))


def test_health_reports_the_service_is_running() -> None:
    response = make_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "urban-road-monitor-ai",
        "version": __version__,
        "graph": {
            "loaded": False,
            "version": None,
            "nodes": None,
            "segments": None,
            "loadedAt": None,
        },
    }


def test_health_reports_the_loaded_graph(sample_payload: GraphPayload) -> None:
    store = GraphStore(lambda: sample_payload, lambda p: build_loaded_graph(p, 200.0))
    store.get()

    graph = make_client(store).get("/health").json()["graph"]

    assert graph["loaded"] is True
    assert graph["version"] == "sample-v1"
    assert (graph["nodes"], graph["segments"]) == (7, 5)
    assert graph["loadedAt"].endswith("Z") or graph["loadedAt"].endswith("+00:00")


def test_health_never_exposes_the_token() -> None:
    response = make_client().get("/health")

    assert TOKEN not in response.text


def test_health_is_listed_in_the_api_documentation() -> None:
    response = make_client().get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
