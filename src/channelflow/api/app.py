"""The application, assembled.

# @trace: REQ-API-001
"""

from __future__ import annotations

from fastapi import FastAPI

from channelflow.api.metrics_route import router as metrics_router
from channelflow.api.repositories import Repository
from channelflow.api.routes import router
from channelflow.api.ws import register_websocket
from channelflow.metrics import MetricRegistry


def create_app(*, repository: Repository, metrics: MetricRegistry | None = None) -> FastAPI:
    """Build the app over a repository (ADR-019).

    A factory rather than a module-level singleton: the tests build one per
    fixture, and a global would make them share state in the order they happen
    to run.

    The registry is an argument for the same reason. A process wires in the one
    its components observe into; an app built without one serves an empty
    exposition, which is the honest answer for a process that has measured
    nothing rather than an error.
    """
    app = FastAPI(title="ChannelFlow read API", version="1.0.0")
    app.state.repository = repository
    app.state.metrics = metrics or MetricRegistry()
    app.include_router(router)
    app.include_router(metrics_router)
    register_websocket(app)
    return app
