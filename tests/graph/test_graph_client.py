"""The graph client against a fake backend: no network and no real waiting."""

import json

import httpx2
import pytest

from app.graph.client import (
    MAX_ATTEMPTS,
    RETRY_PAUSE_S,
    BackendGraphClient,
    GraphDownloadError,
)

TOKEN = "0123456789abcdef" * 4
BACKEND = "https://backend.example.com"
GRAPH = {
    "version": "940ab0350236d4a94de0b11d6ed78931",
    "nodes": [
        {"id": 11, "latitude": 1.214, "longitude": -77.281},
        {"id": 12, "latitude": 1.2141, "longitude": -77.28},
    ],
    "segments": [
        {
            "id": 7,
            "fromNodeId": 11,
            "toNodeId": 12,
            "lengthM": 112.0,
            "damageScore": 2.0,
            "isOneway": False,
        }
    ],
}


class FakeBackend:
    """Answers each request with the next reply of a list, and records the requests."""

    def __init__(self, *replies: httpx2.Response | Exception) -> None:
        self.replies = list(replies)
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def make_client(backend: FakeBackend, pauses: list[float]) -> BackendGraphClient:
    return BackendGraphClient(
        BACKEND, TOKEN, transport=httpx2.MockTransport(backend), sleep=pauses.append
    )


def ok() -> httpx2.Response:
    return httpx2.Response(200, json=GRAPH)


def status(code: int) -> httpx2.Response:
    return httpx2.Response(code, json={"error": {"code": "X", "message": "x"}})


def test_downloads_and_reads_the_graph_in_camel_case() -> None:
    backend = FakeBackend(ok())

    payload = make_client(backend, []).fetch()

    assert payload.version == GRAPH["version"]
    assert [node.id for node in payload.nodes] == [11, 12]
    segment = payload.segments[0]
    assert (segment.from_node_id, segment.to_node_id, segment.length_m) == (11, 12, 112.0)
    assert (segment.damage_score, segment.is_oneway) == (2.0, False)


def test_asks_the_internal_graph_endpoint_with_the_token() -> None:
    backend = FakeBackend(ok())

    make_client(backend, []).fetch()

    request = backend.requests[0]
    assert request.method == "GET"
    assert str(request.url) == f"{BACKEND}/internal/graph"
    assert request.headers["authorization"] == f"Bearer {TOKEN}"
    assert "gzip" in request.headers["accept-encoding"]


@pytest.mark.parametrize(
    "first_failure",
    [
        httpx2.ConnectError("connection refused"),
        httpx2.ReadTimeout("timed out"),
        status(502),
        status(503),
        status(504),
    ],
    ids=["connect-error", "timeout", "502", "503", "504"],
)
def test_tries_again_once_when_the_backend_may_be_starting(
    first_failure: httpx2.Response | Exception,
) -> None:
    backend = FakeBackend(first_failure, ok())
    pauses: list[float] = []

    payload = make_client(backend, pauses).fetch()

    assert payload.version == GRAPH["version"]
    assert len(backend.requests) == 2
    assert pauses == [RETRY_PAUSE_S]


def test_gives_up_after_two_attempts() -> None:
    backend = FakeBackend(status(503), status(503))
    pauses: list[float] = []

    with pytest.raises(GraphDownloadError, match="is starting") as error:
        make_client(backend, pauses).fetch()

    assert error.value.retryable
    assert len(backend.requests) == MAX_ATTEMPTS == 2
    assert pauses == [RETRY_PAUSE_S]


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        (status(401), "rejected INTERNAL_TOKEN"),
        (status(404), "INTERNAL_TOKEN is not configured there"),
        (status(500), r"unexpected answer from the backend \(HTTP 500\)"),
        (httpx2.Response(200, content=b"<html>not json</html>"), "not valid"),
        (httpx2.Response(200, json={"version": "v", "nodes": []}), "not valid"),
        (httpx2.Response(200, json={**GRAPH, "version": ""}), "not valid"),
    ],
    ids=["401", "404", "500", "not-json", "missing-segments", "empty-version"],
)
def test_does_not_try_again_when_it_cannot_help(reply: httpx2.Response, message: str) -> None:
    backend = FakeBackend(reply)
    pauses: list[float] = []

    with pytest.raises(GraphDownloadError, match=message) as error:
        make_client(backend, pauses).fetch()

    assert not error.value.retryable
    assert len(backend.requests) == 1
    assert pauses == []


def test_never_follows_a_redirect_so_the_token_stays_with_the_backend() -> None:
    backend = FakeBackend(
        httpx2.Response(302, headers={"location": "https://somewhere-else.example.com/steal"})
    )

    with pytest.raises(GraphDownloadError, match="redirect"):
        make_client(backend, []).fetch()

    assert [request.url.host for request in backend.requests] == ["backend.example.com"]


def test_never_writes_the_token_in_logs_or_errors(caplog: pytest.LogCaptureFixture) -> None:
    backend = FakeBackend(httpx2.ConnectError("refused"), status(401))

    with pytest.raises(GraphDownloadError) as error:
        make_client(backend, []).fetch()

    assert TOKEN not in str(error.value)
    assert TOKEN not in caplog.text
    assert "backend.example.com" in caplog.text


def test_reads_a_large_graph() -> None:
    nodes = [{"id": i, "latitude": 1.2 + i / 1e5, "longitude": -77.28} for i in range(5_000)]
    segments = [
        {
            "id": i,
            "fromNodeId": i,
            "toNodeId": i + 1,
            "lengthM": 1.2,
            "damageScore": 0.0,
            "isOneway": i % 2 == 0,
        }
        for i in range(4_999)
    ]
    body = json.dumps({"version": "big", "nodes": nodes, "segments": segments})
    backend = FakeBackend(httpx2.Response(200, content=body.encode()))

    payload = make_client(backend, []).fetch()

    assert (len(payload.nodes), len(payload.segments)) == (5_000, 4_999)
