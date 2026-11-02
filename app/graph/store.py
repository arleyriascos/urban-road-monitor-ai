"""The road graph kept in memory, and the rules to load and refresh it.

1. One download at a time: a lock makes simultaneous requests wait for the same
   download instead of starting their own.
2. Atomic change: the new graph is built completely before it replaces the old one;
   requests already running finish with the graph they started with.
3. A request whose graphVersion differs from the loaded one triggers a reload, except
   within 10 s of the last download, when the current graph is used.
4. The version kept is the one that came with the download, not the one requested.
5. If a reload fails and a graph is loaded, that graph keeps serving routes; with no
   graph at all, GraphUnavailableError. After a failure there is no new try for 10 s.
6. Invalid data (the graph rejects it) never replaces the graph already loaded.
"""

import contextlib
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app.graph.client import GraphDownloadError
from app.graph.payload import GraphPayload
from app.routing.locator import NodeLocator
from app.structures.graph import GraphError, RoadGraph

logger = logging.getLogger(__name__)

COOLDOWN_S = 10.0


class GraphUnavailableError(Exception):
    """There is no road graph loaded and it could not be downloaded."""


@dataclass(frozen=True, slots=True)
class LoadedGraph:
    """A complete road graph, ready to answer routes. It is never modified."""

    version: str
    graph: RoadGraph
    locator: NodeLocator
    loaded_at: datetime

    @property
    def node_count(self) -> int:
        return self.graph.node_count

    @property
    def segment_count(self) -> int:
        return self.graph.segment_count


def build_loaded_graph(payload: GraphPayload, max_snap_distance_m: float) -> LoadedGraph:
    """Build the graph and the click locator. Raises GraphError on invalid data."""
    graph = RoadGraph()
    for node in payload.nodes:
        graph.add_node(node.id, node.latitude, node.longitude)
    for segment in payload.segments:
        graph.add_segment(
            segment.id,
            segment.from_node_id,
            segment.to_node_id,
            segment.length_m,
            segment.damage_score,
            segment.is_oneway,
        )
    return LoadedGraph(
        version=payload.version,
        graph=graph,
        locator=NodeLocator(graph, max_snap_distance_m),
        loaded_at=datetime.now(UTC),
    )


class GraphStore:
    """Holds the current road graph and reloads it following the rules above."""

    def __init__(
        self,
        fetch: Callable[[], GraphPayload],
        build: Callable[[GraphPayload], LoadedGraph],
        *,
        cooldown_s: float = COOLDOWN_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._fetch = fetch
        self._build = build
        self._cooldown_s = cooldown_s
        self._clock = clock
        self._lock = threading.Lock()
        self._current: LoadedGraph | None = None
        self._last_download: float | None = None
        """When the last download ended, successful or not."""

    @property
    def current(self) -> LoadedGraph | None:
        return self._current

    def get(self, wanted_version: str | None = None) -> LoadedGraph:
        """The graph to answer with. None means any loaded graph will do."""
        current = self._current
        if current is not None and wanted_version in (None, current.version):
            return current

        with self._lock:
            # Another request may have finished the download while this one waited.
            current = self._current
            if current is not None and wanted_version in (None, current.version):
                return current
            if self._in_cooldown():
                if current is not None:
                    return current
                raise GraphUnavailableError(
                    "the last download of the road graph failed moments ago"
                )
            return self._reload(current)

    def warm_up(self) -> None:
        """Load the graph in the background when the service starts."""
        # A failure is already logged; the first route request will try again.
        with contextlib.suppress(GraphUnavailableError):
            self.get()

    def _in_cooldown(self) -> bool:
        return (
            self._last_download is not None
            and self._clock() - self._last_download < self._cooldown_s
        )

    def _reload(self, current: LoadedGraph | None) -> LoadedGraph:
        try:
            loaded = self._build(self._fetch())
        except (GraphDownloadError, GraphError) as error:
            return self._keep(current, error, f"Could not load the road graph: {error}")
        except Exception as error:
            logger.exception("Unexpected error while loading the road graph")
            return self._keep(current, error, None)
        finally:
            self._last_download = self._clock()

        self._current = loaded
        logger.info(
            "Loaded road graph %s: %d nodes, %d segments",
            loaded.version,
            loaded.node_count,
            loaded.segment_count,
        )
        return loaded

    def _keep(
        self, current: LoadedGraph | None, error: Exception, message: str | None
    ) -> LoadedGraph:
        if message is not None:
            logger.error(message)
        if current is None:
            raise GraphUnavailableError("the road graph could not be loaded") from error
        logger.warning("Still answering with the road graph %s", current.version)
        return current
