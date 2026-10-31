"""Entry point of the AI service: builds the FastAPI application."""

from fastapi import FastAPI

from app import __version__
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the application. Tests pass their own settings; production reads the environment."""
    app = FastAPI(
        title="Urban Road Monitor AI",
        version=__version__,
        description="Route computation and pothole clustering for Urban Road Monitor.",
    )
    app.state.settings = settings if settings is not None else Settings()
    return app


app = create_app()
