"""The application, assembled.

# @trace: REQ-API-001
"""

from __future__ import annotations

from fastapi import FastAPI

from channelflow.api.repositories import Repository
from channelflow.api.routes import router
from channelflow.api.ws import register_websocket


def create_app(*, repository: Repository) -> FastAPI:
    """Build the app over a repository (ADR-019).

    A factory rather than a module-level singleton: the tests build one per
    fixture, and a global would make them share state in the order they happen
    to run.
    """
    app = FastAPI(title="ChannelFlow read API", version="1.0.0")
    app.state.repository = repository
    app.include_router(router)
    register_websocket(app)
    return app
