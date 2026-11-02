"""Downloads the road graph from the backend (GET /internal/graph).

- Waits up to 10 s to connect and 45 s to read: Render holds the request while a
  sleeping backend starts, so a long wait covers the wake-up.
- Two attempts at most, 3 s apart, and only when trying again can help: a failed
  connection, a timeout, or 502/503/504 while the backend starts.
- 401 and 404 are configuration errors: trying again does not fix them, so they are
  reported at once with what to check.
- Redirects are not followed, so the token is never sent to another address.
- The token is never logged: messages only name the backend host.
"""

import logging
import time
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx2
from pydantic import ValidationError

from app.graph.payload import GraphPayload

logger = logging.getLogger(__name__)

GRAPH_PATH = "/internal/graph"
CONNECT_TIMEOUT_S = 10.0
READ_TIMEOUT_S = 45.0
MAX_ATTEMPTS = 2
RETRY_PAUSE_S = 3.0
RETRYABLE_STATUS = frozenset({502, 503, 504})


class GraphDownloadError(Exception):
    """The graph could not be downloaded. ``retryable`` tells if trying again may help."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class BackendGraphClient:
    """HTTP client of the backend's internal graph endpoint."""

    def __init__(
        self,
        backend_url: str,
        token: str,
        *,
        transport: httpx2.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._host = urlsplit(backend_url).netloc
        self._sleep = sleep
        self._client = httpx2.Client(
            base_url=backend_url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=httpx2.Timeout(
                connect=CONNECT_TIMEOUT_S, read=READ_TIMEOUT_S, write=10.0, pool=10.0
            ),
            follow_redirects=False,
            transport=transport,
        )

    def fetch(self) -> GraphPayload:
        """Download and check the graph, trying a second time when that can help."""
        attempt = 1
        while True:
            try:
                return self._fetch_once()
            except GraphDownloadError as error:
                if not error.retryable or attempt >= MAX_ATTEMPTS:
                    raise
                logger.warning(
                    "Graph download failed (%s); trying again in %.0f s", error, RETRY_PAUSE_S
                )
                self._sleep(RETRY_PAUSE_S)
                attempt += 1

    def close(self) -> None:
        self._client.close()

    def _fetch_once(self) -> GraphPayload:
        try:
            response = self._client.get(GRAPH_PATH)
        except httpx2.TimeoutException as error:
            raise GraphDownloadError(
                f"the backend at {self._host} did not answer in time", retryable=True
            ) from error
        except httpx2.TransportError as error:
            raise GraphDownloadError(
                f"could not connect to the backend at {self._host}", retryable=True
            ) from error

        status = response.status_code
        if status == 200:
            try:
                return GraphPayload.model_validate_json(response.content)
            except ValidationError as error:
                raise GraphDownloadError(
                    "the backend sent a road graph that is not valid", retryable=False
                ) from error
        if status in RETRYABLE_STATUS:
            raise GraphDownloadError(
                f"the backend at {self._host} is starting (HTTP {status})", retryable=True
            )
        if status == 401:
            raise GraphDownloadError(
                "the backend rejected INTERNAL_TOKEN: it must be the same value in both services",
                retryable=False,
            )
        if status == 404:
            raise GraphDownloadError(
                "the backend answered 404: INTERNAL_TOKEN is not configured there", retryable=False
            )
        if 300 <= status < 400:
            raise GraphDownloadError(
                f"the backend answered with a redirect (HTTP {status}); it is not followed, "
                "so the token stays with BACKEND_URL",
                retryable=False,
            )
        raise GraphDownloadError(
            f"unexpected answer from the backend (HTTP {status})", retryable=False
        )
