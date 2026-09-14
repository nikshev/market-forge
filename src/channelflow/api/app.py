"""The application, assembled.

# @trace: REQ-API-001
# @trace: REQ-WP-072
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from channelflow.api.metrics_route import router as metrics_router
from channelflow.api.readiness import Probe, always_ready
from channelflow.api.readiness import router as readiness_router
from channelflow.api.repositories import Repository
from channelflow.api.routes import router
from channelflow.api.security import FixedWindowLimiter, RateLimitMiddleware
from channelflow.api.ws import register_websocket
from channelflow.metrics import MetricRegistry
from channelflow.settings import RateLimit


def create_app(
    *,
    repository: Repository,
    metrics: MetricRegistry | None = None,
    readiness: Probe | None = None,
    allowed_origins: tuple[str, ...] = (),
    rate_limit: RateLimit | None = None,
    clock: Callable[[], float] = time.monotonic,
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
    if rate_limit is not None:
        app.add_middleware(RateLimitMiddleware, limiter=FixedWindowLimiter(rate_limit, clock=clock))
    if allowed_origins:
        # Installed only when there is something to allow. With no origins the
        # middleware is absent rather than present-and-empty, so no response
        # carries a CORS header at all -- which is the restriction §34 wants,
        # and is what this application did before any of this existed.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(allowed_origins),
            allow_methods=["GET"],
            allow_headers=["*"],
        )
    app.state.repository = repository
    app.state.metrics = metrics or MetricRegistry()
    app.include_router(router)
    app.state.readiness = readiness or always_ready()
    app.include_router(metrics_router)
    app.include_router(readiness_router)
    register_websocket(app)
    return app
