"""What the API refuses (REQ-WP-072).

PRD §34 asks for authenticated write routes, restricted CORS and a rate limited
public API. Two of those three hold today by absence: there are no write routes
and no CORS configuration. These tests make the absence deliberate, so the first
`POST` and the first wildcard origin are a red suite rather than a quiet breach.

**The route walk is the load-bearing part.** FastAPI 0.141.1 does not flatten
included routers: `app.routes` holds four `Route`s, three `_IncludedRouter`s and
one `APIWebSocketRoute`, and an `_IncludedRouter` exposes neither `.path` nor
`.routes` -- the way in is `.original_router`. A naive walk reaches five of the
seventeen routes, misses everything under `/api/v1`, finds no offending method
and reports success. So the count is asserted alongside the property: it is what
separates "no offending routes" from "no routes".
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from channelflow.api.app import create_app
from channelflow.api.repositories import InMemoryRepository
from channelflow.api.security import (
    FixedWindowLimiter,
    all_routes,
    offending_routes,
)
from channelflow.settings import RateLimit

#: Thirteen API routes, four documentation routes, one websocket.
#: `timeframes` joined the API routes with REQ-WP-074.
EXPECTED_ROUTES = 18


@pytest.fixture
def app() -> FastAPI:
    return create_app(repository=InMemoryRepository())


# --- T011-T015: the route gate ----------------------------------------------


@pytest.mark.trace("REQ-WP-072")
def test_the_walk_reaches_every_route(app: FastAPI) -> None:
    """Without this the gate below passes on a walk that reaches nothing."""
    assert len(all_routes(app)) == EXPECTED_ROUTES
    paths = {path for path, _ in all_routes(app)}
    assert "/api/v1/markets" in paths, "an included router was not descended into"
    assert "/ws/market" in paths
    assert "/openapi.json" in paths


@pytest.mark.trace("REQ-WP-072")
def test_no_route_does_anything_but_read(app: FastAPI) -> None:
    assert offending_routes(app, authenticated=frozenset()) == []


@pytest.mark.trace("REQ-WP-072")
def test_the_websocket_is_recognised_rather_than_slipping_through(app: FastAPI) -> None:
    """A websocket route carries no methods; a method check alone ignores it."""
    methods = dict(all_routes(app))
    assert methods["/ws/market"] == frozenset()


@pytest.mark.trace("REQ-WP-072")
def test_a_write_route_is_reported_by_path_and_method(app: FastAPI) -> None:
    @app.post("/api/v1/orders")
    def place() -> dict[str, str]:  # pragma: no cover - never called
        return {}

    offending = offending_routes(app, authenticated=frozenset())
    assert offending == [("/api/v1/orders", ["POST"])]


@pytest.mark.trace("REQ-WP-072")
def test_a_write_route_behind_authentication_is_permitted(app: FastAPI) -> None:
    @app.post("/api/v1/orders")
    def place() -> dict[str, str]:  # pragma: no cover - never called
        return {}

    assert offending_routes(app, authenticated=frozenset({"/api/v1/orders"})) == []


@pytest.mark.trace("REQ-WP-072")
@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_every_write_method_is_caught_not_only_post(app: FastAPI, method: str) -> None:
    getattr(app, method)("/api/v1/thing")(lambda: {})  # pragma: no cover
    offending = offending_routes(app, authenticated=frozenset())
    assert [path for path, _ in offending] == ["/api/v1/thing"]


# --- T016-T019: CORS --------------------------------------------------------


@pytest.mark.trace("REQ-WP-072")
def test_with_no_origins_no_cors_header_is_ever_sent() -> None:
    app = create_app(repository=InMemoryRepository(), allowed_origins=())
    client = TestClient(app)
    response = client.get("/readyz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


@pytest.mark.trace("REQ-WP-072")
def test_a_configured_origin_is_allowed_and_another_is_not() -> None:
    app = create_app(repository=InMemoryRepository(), allowed_origins=("https://a.example",))
    client = TestClient(app)
    allowed = client.get("/readyz", headers={"Origin": "https://a.example"})
    assert allowed.headers["access-control-allow-origin"] == "https://a.example"
    refused = client.get("/readyz", headers={"Origin": "https://b.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in refused.headers}


# --- T020-T026: the limiter -------------------------------------------------


class Clock:
    """A clock the test moves. The limiter cannot tell it from a real one."""

    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.trace("REQ-WP-072")
def test_three_are_allowed_and_the_fourth_is_not() -> None:
    clock = Clock()
    limiter = FixedWindowLimiter(RateLimit(requests=3, window_seconds=60), clock=clock)
    assert [limiter.allow("a").allowed for _ in range(4)] == [True, True, True, False]


@pytest.mark.trace("REQ-WP-072")
def test_the_window_has_to_pass_entirely() -> None:
    clock = Clock()
    limiter = FixedWindowLimiter(RateLimit(requests=1, window_seconds=60), clock=clock)
    assert limiter.allow("a").allowed is True
    clock.now += 59.0
    assert limiter.allow("a").allowed is False
    clock.now += 1.5
    assert limiter.allow("a").allowed is True


@pytest.mark.trace("REQ-WP-072")
def test_a_refusal_says_how_long_to_wait() -> None:
    clock = Clock()
    limiter = FixedWindowLimiter(RateLimit(requests=1, window_seconds=60), clock=clock)
    limiter.allow("a")
    clock.now += 20.0
    decision = limiter.allow("a")
    assert decision.allowed is False
    assert decision.retry_after_seconds == pytest.approx(40.0)


@pytest.mark.trace("REQ-WP-072")
def test_two_clients_do_not_share_a_budget() -> None:
    clock = Clock()
    limiter = FixedWindowLimiter(RateLimit(requests=1, window_seconds=60), clock=clock)
    assert limiter.allow("a").allowed is True
    assert limiter.allow("b").allowed is True
    assert limiter.allow("a").allowed is False


@pytest.mark.trace("REQ-WP-072")
def test_a_refused_request_is_a_refusal_not_a_late_success() -> None:
    """Checked on the status and the headers. Timing here would measure the machine."""
    clock = Clock()
    app = create_app(
        repository=InMemoryRepository(),
        rate_limit=RateLimit(requests=2, window_seconds=60),
        clock=clock,
    )
    client = TestClient(app)
    codes = [client.get("/api/v1/markets").status_code for _ in range(3)]
    assert codes[:2] == [200, 200]
    assert codes[2] == 429
    refused = client.get("/api/v1/markets")
    assert refused.status_code == 429
    assert int(refused.headers["retry-after"]) > 0


@pytest.mark.trace("REQ-WP-072")
def test_readiness_and_metrics_are_never_throttled() -> None:
    """Throttling a readiness probe is the outage the limiter exists to prevent."""
    clock = Clock()
    app = create_app(
        repository=InMemoryRepository(),
        rate_limit=RateLimit(requests=1, window_seconds=60),
        clock=clock,
    )
    client = TestClient(app)
    client.get("/api/v1/markets")
    assert client.get("/api/v1/markets").status_code == 429
    for _ in range(5):
        assert client.get("/readyz").status_code in {200, 503}
        assert client.get("/metrics").status_code == 200


@pytest.mark.trace("REQ-WP-072")
def test_without_a_limit_nothing_is_refused() -> None:
    app = create_app(repository=InMemoryRepository(), rate_limit=None)
    client = TestClient(app)
    assert {client.get("/api/v1/markets").status_code for _ in range(20)} == {200}


@pytest.mark.trace("REQ-WP-072")
def test_the_limiter_keeps_one_row_per_key_not_one_per_request() -> None:
    """A fixed window keeps a count, not a log.

    Counted across several keys as well as many requests: asserting only that
    one key costs one row is satisfied by a function that always answers one.
    """
    clock = Clock()
    limiter = FixedWindowLimiter(RateLimit(requests=10, window_seconds=60), clock=clock)
    for _ in range(1_000):
        limiter.allow("a")
    assert limiter.tracked_keys() == 1
    for key in ("b", "c", "d"):
        limiter.allow(key)
    assert limiter.tracked_keys() == 4


# --- T040a: no services, no network -----------------------------------------


@pytest.mark.trace("REQ-WP-072")
def test_these_tests_reach_nothing_outside_the_process() -> None:
    """Checked on the imports, not on substrings: "socket" lives in "websocket"."""
    import ast
    from pathlib import Path

    imported: set[str] = set()
    for node in ast.walk(ast.parse(Path(__file__).read_text())):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert imported, "parsed no imports; the check would pass vacuously"
    forbidden = {"socket", "urllib", "http", "requests", "httpx"}
    reached = {name for name in imported if name.split(".")[0] in forbidden}
    assert reached == set(), f"{reached} would make these tests need a network"
    assert not any(name.startswith("tools.record") for name in imported)
