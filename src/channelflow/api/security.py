"""What the read API refuses (PRD §34).

# @trace: REQ-WP-072

Three things §34 asks for, in one module because they are one subject: what a
route is allowed to be, which origins may read it, and how often.

**The route walk is the load-bearing part, and the obvious version of it does
not work.** FastAPI does not flatten included routers into `app.routes`: that
list holds the documentation routes, one object per `include_router` call, and
the websocket. Those per-router objects expose neither `.path` nor `.routes` --
the way in is `.original_router`. Measured on this application: a walk that does
not descend reaches **5 of 17** routes, misses everything under `/api/v1`, finds
no offending method and reports success. Any caller of `offending_routes` must
therefore also assert how many routes were walked; "nothing offends" and
"nothing was looked at" are otherwise the same answer.

**The limiter counts in one process.** With N API processes the effective limit
is N times the configured one -- written here and in the deployment document
rather than discovered. A shared counter needs a store, [[ADR-002]] dropped the
one this stack had, and building for a second process before there is one is
designing against a guess.

A fixed window, not a sliding log: it admits up to twice the limit across a
boundary, which is a sentence, where a sliding log's cost is per-key storage
proportional to the limit. Principle XII, and the simpler thing whose failure
mode fits in a sentence.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from channelflow.settings import RateLimit

#: Methods a read API may answer. `HEAD` is here because Starlette adds it to
#: every `GET` route -- excluding it would fail on four documentation routes
#: nobody wrote.
READ_METHODS = frozenset({"GET", "HEAD"})

#: Paths the limiter never refuses. Throttling a readiness probe makes an
#: orchestrator declare the service unhealthy: the limiter causing the outage it
#: exists to prevent. A scrape interval is already a rate limit.
UNLIMITED_PATHS = frozenset({"/readyz", "/metrics"})

#: PRD §34's "rate limiting for public web API", as a client sees it.
TOO_MANY_REQUESTS = 429


def all_routes(app: FastAPI) -> list[tuple[str, frozenset[str]]]:
    """Every route the application registers, with its methods.

    A websocket route carries no methods and appears with an empty set rather
    than being dropped: a method check alone would ignore it, and "no methods"
    is exactly what a naive gate reads as harmless.
    """

    def walk(routes: Iterable[Any]) -> Iterable[tuple[str, frozenset[str]]]:
        for route in routes:
            included = getattr(route, "original_router", None)
            if included is not None:
                yield from walk(included.routes)
                continue
            path = getattr(route, "path", None)
            if path is None:
                continue
            yield path, frozenset(getattr(route, "methods", None) or ())

    return list(walk(app.routes))


def offending_routes(app: FastAPI, *, authenticated: frozenset[str]) -> list[tuple[str, list[str]]]:
    """Routes that do more than read and are not behind authentication.

    `authenticated` is empty today, and that is the point: the first write route
    has to be named here, by somebody who has decided it should exist.
    """
    offending = []
    for path, methods in all_routes(app):
        if path in authenticated or methods <= READ_METHODS:
            continue
        offending.append((path, sorted(methods - READ_METHODS)))
    return offending


@dataclass(frozen=True)
class Decision:
    """Whether this request is served, and when to come back if not."""

    allowed: bool
    retry_after_seconds: float


class FixedWindowLimiter:
    """A count per key per window.

    The clock is an argument because Principle VII forbids a test-only branch:
    the tests drive the same code a deployment runs, with a clock they control.
    """

    def __init__(self, limit: RateLimit, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._clock = clock
        #: key -> (window started at, count so far). One entry per key, not one
        #: per request: the memory a key costs does not grow with its traffic.
        self._windows: dict[str, tuple[float, int]] = {}

    def allow(self, key: str) -> Decision:
        now = self._clock()
        started, count = self._windows.get(key, (now, 0))
        if now - started >= self._limit.window_seconds:
            started, count = now, 0
        if count >= self._limit.requests:
            self._windows[key] = (started, count)
            return Decision(
                allowed=False,
                retry_after_seconds=started + self._limit.window_seconds - now,
            )
        self._windows[key] = (started, count + 1)
        return Decision(allowed=True, retry_after_seconds=0.0)

    def tracked_keys(self) -> int:
        return len(self._windows)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Refuses immediately rather than delaying.

    A queue would turn a limit into latency, and latency is what a caller reads
    as the service being slow rather than as having said no.
    """

    def __init__(self, app: Any, *, limiter: FixedWindowLimiter) -> None:
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if request.url.path in UNLIMITED_PATHS:
            return await call_next(request)  # type: ignore[no-any-return]
        client = request.client
        decision = self._limiter.allow(client.host if client else "unknown")
        if decision.allowed:
            return await call_next(request)  # type: ignore[no-any-return]
        return JSONResponse(
            {"detail": "too many requests"},
            status_code=TOO_MANY_REQUESTS,
            # Whole seconds, rounded up: a `Retry-After` of 0 invites an
            # immediate retry that is refused again.
            headers={"Retry-After": str(max(1, int(decision.retry_after_seconds) + 1))},
        )
