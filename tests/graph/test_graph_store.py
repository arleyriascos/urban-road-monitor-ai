"""The rules to load and refresh the road graph, with a fake download and a fake clock."""

import threading
import time
from datetime import UTC

import pytest

from app.graph.client import GraphDownloadError
from app.graph.payload import GraphPayload, GraphSegmentIn
from app.graph.store import (
    COOLDOWN_S,
    GraphStore,
    GraphUnavailableError,
    LoadedGraph,
    build_loaded_graph,
)
from app.structures.graph import GraphError


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeDownload:
    """Returns the next payload or raises the next error, and counts the downloads."""

    def __init__(self, *replies: GraphPayload | Exception) -> None:
        self.replies = list(replies)
        self.calls = 0

    def __call__(self) -> GraphPayload:
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def versioned(payload: GraphPayload, version: str) -> GraphPayload:
    return payload.model_copy(update={"version": version})


def build(payload: GraphPayload) -> LoadedGraph:
    return build_loaded_graph(payload, 200.0)


def make_store(download: FakeDownload, clock: FakeClock) -> GraphStore:
    return GraphStore(download, build, clock=clock)


def test_builds_the_graph_and_the_locator_from_the_backend_data(
    sample_payload: GraphPayload,
) -> None:
    loaded = build(sample_payload)

    assert loaded.version == "sample-v1"
    assert (loaded.node_count, loaded.segment_count) == (7, 5)
    assert loaded.locator.main_component_size == 5
    assert loaded.loaded_at.tzinfo is UTC


def test_loads_the_graph_the_first_time_it_is_needed(sample_payload: GraphPayload) -> None:
    download = FakeDownload(sample_payload)
    store = make_store(download, FakeClock())

    assert store.current is None
    loaded = store.get("sample-v1")

    assert loaded.version == "sample-v1"
    assert store.current is loaded
    assert download.calls == 1


def test_does_not_download_again_when_the_version_matches(sample_payload: GraphPayload) -> None:
    download = FakeDownload(sample_payload)
    clock = FakeClock()
    store = make_store(download, clock)
    first = store.get("sample-v1")

    clock.advance(3_600)
    again = store.get("sample-v1")
    any_version = store.get()

    assert again is first
    assert any_version is first
    assert download.calls == 1


def test_reloads_when_the_version_changes(sample_payload: GraphPayload) -> None:
    download = FakeDownload(sample_payload, versioned(sample_payload, "sample-v2"))
    clock = FakeClock()
    store = make_store(download, clock)
    store.get("sample-v1")

    clock.advance(COOLDOWN_S)
    loaded = store.get("sample-v2")

    assert loaded.version == "sample-v2"
    assert download.calls == 2
    # The new graph is kept: the next requests use it without downloading again.
    assert store.current is loaded
    assert store.get("sample-v2") is loaded
    assert download.calls == 2


def test_keeps_the_version_that_came_with_the_download(sample_payload: GraphPayload) -> None:
    # The backend asked for v2, but by the time of the download the graph was already v3.
    download = FakeDownload(versioned(sample_payload, "sample-v3"))
    store = make_store(download, FakeClock())

    loaded = store.get("sample-v2")

    assert loaded.version == "sample-v3"


def test_uses_the_current_graph_within_the_cooldown(sample_payload: GraphPayload) -> None:
    download = FakeDownload(sample_payload, versioned(sample_payload, "sample-v2"))
    clock = FakeClock()
    store = make_store(download, clock)
    first = store.get("sample-v1")

    clock.advance(COOLDOWN_S - 0.5)
    loaded = store.get("an-older-version")

    assert loaded is first
    assert download.calls == 1

    clock.advance(1.0)
    assert store.get("sample-v2").version == "sample-v2"
    assert download.calls == 2


def test_keeps_answering_with_the_old_graph_if_a_reload_fails(
    sample_payload: GraphPayload, caplog: pytest.LogCaptureFixture
) -> None:
    failure = GraphDownloadError("could not connect to the backend at x", retryable=True)
    download = FakeDownload(sample_payload, failure)
    clock = FakeClock()
    store = make_store(download, clock)
    first = store.get("sample-v1")

    clock.advance(COOLDOWN_S)
    loaded = store.get("sample-v2")

    assert loaded is first
    assert "Could not load the road graph: could not connect" in caplog.text
    assert "Still answering with the road graph sample-v1" in caplog.text


def test_does_not_try_again_right_after_a_failure(sample_payload: GraphPayload) -> None:
    failure = GraphDownloadError("the backend at x is starting (HTTP 503)", retryable=True)
    download = FakeDownload(failure, sample_payload)
    clock = FakeClock()
    store = make_store(download, clock)

    with pytest.raises(GraphUnavailableError):
        store.get("sample-v1")
    with pytest.raises(GraphUnavailableError, match="moments ago"):
        store.get("sample-v1")
    assert download.calls == 1

    clock.advance(COOLDOWN_S)
    assert store.get("sample-v1").version == "sample-v1"
    assert download.calls == 2


def test_invalid_data_never_replaces_the_loaded_graph(sample_payload: GraphPayload) -> None:
    broken = sample_payload.model_copy(
        update={
            "version": "broken",
            "segments": [
                *sample_payload.segments,
                GraphSegmentIn(
                    id=9_999,
                    from_node_id=101,
                    to_node_id=404,  # not in the node list
                    length_m=10.0,
                    damage_score=0.0,
                    is_oneway=False,
                ),
            ],
        }
    )
    download = FakeDownload(sample_payload, broken)
    clock = FakeClock()
    store = make_store(download, clock)
    first = store.get("sample-v1")

    clock.advance(COOLDOWN_S)
    loaded = store.get("broken")

    assert loaded is first
    assert store.current is first


def test_invalid_data_on_the_first_load_means_no_graph(sample_payload: GraphPayload) -> None:
    too_short = sample_payload.model_copy(
        update={
            "segments": [
                segment.model_copy(update={"length_m": 50.0}) if segment.id == 1001 else segment
                for segment in sample_payload.segments
            ]
        }
    )
    store = make_store(FakeDownload(too_short), FakeClock())

    with pytest.raises(GraphUnavailableError) as error:
        store.get()

    assert isinstance(error.value.__cause__, GraphError)


def test_an_unexpected_error_keeps_the_service_alive(
    sample_payload: GraphPayload, caplog: pytest.LogCaptureFixture
) -> None:
    download = FakeDownload(sample_payload, RuntimeError("bug in the download"))
    clock = FakeClock()
    store = make_store(download, clock)
    first = store.get()

    clock.advance(COOLDOWN_S)

    assert store.get("sample-v2") is first
    assert "Unexpected error while loading the road graph" in caplog.text


def test_simultaneous_requests_share_one_download(sample_payload: GraphPayload) -> None:
    release = threading.Event()
    calls: list[int] = []

    def slow_download() -> GraphPayload:
        calls.append(1)
        release.wait(timeout=5)
        return sample_payload

    store = GraphStore(slow_download, build)
    results: list[str] = []

    def ask() -> None:
        results.append(store.get("sample-v1").version)

    threads = [threading.Thread(target=ask) for _ in range(8)]
    for thread in threads:
        thread.start()
    time.sleep(0.2)  # every thread is now waiting for the same download
    release.set()
    for thread in threads:
        thread.join(timeout=5)

    assert len(calls) == 1
    assert results == ["sample-v1"] * 8


def test_a_graph_in_use_is_not_changed_by_a_reload(sample_payload: GraphPayload) -> None:
    download = FakeDownload(sample_payload, versioned(sample_payload, "sample-v2"))
    clock = FakeClock()
    store = make_store(download, clock)
    in_use = store.get("sample-v1")
    nodes_before = in_use.node_count

    clock.advance(COOLDOWN_S)
    newer = store.get("sample-v2")

    assert newer is not in_use
    assert in_use.version == "sample-v1"
    assert in_use.node_count == nodes_before


def test_warm_up_loads_the_graph(sample_payload: GraphPayload) -> None:
    store = make_store(FakeDownload(sample_payload), FakeClock())

    store.warm_up()

    assert store.current is not None


def test_warm_up_does_not_raise_when_the_backend_is_down() -> None:
    failure = GraphDownloadError("could not connect to the backend at x", retryable=True)
    store = make_store(FakeDownload(failure), FakeClock())

    store.warm_up()

    assert store.current is None
