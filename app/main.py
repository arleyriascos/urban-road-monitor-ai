"""Entry point of the AI service: builds the FastAPI application."""

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.config import Settings
from app.errors import register_error_handlers
from app.graph.client import BackendGraphClient, GraphDownloadError
from app.graph.payload import GraphPayload
from app.graph.store import GraphStore, LoadedGraph, build_loaded_graph
from app.routes.health import router as health_router
from app.routes.route_search import router as route_router
from app.routing.service import RouteService


def configure_logging() -> None:
    """Show the service's own messages (INFO and above) in the console and in Render."""
    logger = logging.getLogger("app")
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def create_graph_store(settings: Settings) -> GraphStore:
    """The graph comes from the backend, downloaded with the shared token."""
    token = settings.internal_token
    client = (
        BackendGraphClient(settings.backend_url, token.get_secret_value())
        if token is not None
        else None
    )

    def fetch() -> GraphPayload:
        if client is None:
            raise GraphDownloadError("INTERNAL_TOKEN is not configured", retryable=False)
        return client.fetch()

    def build(payload: GraphPayload) -> LoadedGraph:
        return build_loaded_graph(payload, settings.max_snap_distance_m)

    return GraphStore(fetch, build)


def create_app(
    settings: Settings | None = None, store: GraphStore | None = None, *, warm_up: bool = True
) -> FastAPI:
    """Create the application. Tests pass their own settings and store."""
    config = settings if settings is not None else Settings()
    graph_store = store if store is not None else create_graph_store(config)
    configure_logging()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # The graph loads in the background, so starting (and Render's health check)
        # never waits for a backend that may be asleep.
        if warm_up and config.internal_token is not None:
            threading.Thread(target=graph_store.warm_up, name="graph-warm-up", daemon=True).start()
        yield

    app = FastAPI(
        title="Urban Road Monitor AI",
        version=__version__,
        description="Route computation and pothole clustering for Urban Road Monitor.",
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.graph_store = graph_store
    app.state.route_service = RouteService(graph_store)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(route_router)
    return app


app = create_app()
