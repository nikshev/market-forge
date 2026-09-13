"""The application, assembled.

# @trace: REQ-API-001
"""

from __future__ import annotations

from fastapi import FastAPI

from channelflow.api.metrics_route import router as metrics_router
from channelflow.api.readiness import Probe, always_ready
from channelflow.api.readiness import router as readiness_router
from channelflow.api.repositories import Repository
from channelflow.api.routes import router
from channelflow.api.ws import register_websocket
from channelflow.metrics import MetricRegistry


def create_app(
    *,
    repository: Repository,
    metrics: MetricRegistry | None = None,
    readiness: Probe | None = None,
) -> FastAPI:
    """Build the app over a repository (ADR-019).

    A factory rather than a module-level singleton: the tests build one per
    fixture, and a global would make them share state in the order they happen
    to run.

    The registry is an argument for the same reason. A process wires in the one
    its components observe into; an app built without one serves an empty
    exposition, which is the honest answer for a process that has measured
    nothing rather than an error.

    So is the readiness probe ([[REQ-WP-064]]). An app over an in-memory
    repository has no store to be unreachable, and says that rather than
    claiming one answered.
    """
    app = FastAPI(title="ChannelFlow read API", version="1.0.0")
    app.state.repository = repository
    app.state.metrics = metrics or MetricRegistry()
    app.include_router(router)
    app.state.readiness = readiness or always_ready()
    app.include_router(metrics_router)
    app.include_router(readiness_router)
    register_websocket(app)
    return app
