"""The API gate: what an unsigned caller gets, and what a signed one still gets (REQ-WP-080).

Mode `required` must close **every** route under `/api/v1`, including the one added next month. A
gate
checked on the three routes someone remembered would pass beside a fourth that is open, and a naive
walk of `app.routes` reaches 5 of 17 routes (REQ-WP-072's measurement), finds nothing wrong and
reports
success. So the walk goes through `all_routes`, which descends, and the count walked is asserted.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from channelflow.api.app import create_app
from channelflow.api.repositories import InMemoryRepository
from channelflow.api.routes import router
from channelflow.api.security import all_routes
from channelflow.api.telegram_auth import TelegramGate

TOKEN = "123456:TEST-TOKEN-NOT-A-SECRET"
NOW = 1_790_000_000.0
MAX_AGE = 86_400
REASONS = {
    "missing_hash",
    "bad_signature",
    "missing_auth_date",
    "malformed",
    "too_old",
    "from_the_future",
}


def _signed(auth_date: float = NOW - 5) -> str:
    fields = {"query_id": "AAx", "auth_date": str(int(auth_date))}
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    return urlencode(
        {**fields, "hash": hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()}
    )


def _gate() -> TelegramGate:
    return TelegramGate(bot_token=TOKEN, max_age_seconds=MAX_AGE, clock=lambda: NOW)


def _app(*, required: bool):  # type: ignore[no-untyped-def]
    return create_app(repository=InMemoryRepository(), telegram_gate=_gate() if required else None)


def _data_routes() -> list[tuple[str, set[str]]]:
    return [
        (path, methods)
        for path, methods in all_routes(_app(required=False))
        if path.startswith("/api/v1")
    ]


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


# --- the walk -------------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-080")
def test_the_walk_reaches_every_data_route_the_router_registers() -> None:
    """If this fails, every test below is vacuous: 'nothing is open' and 'nothing was looked at'
    read
    the same."""
    walked = _data_routes()

    registered = [r for r in router.routes if getattr(r, "path", "").startswith("/api/v1")]
    assert len(walked) == len(registered) > 0


@pytest.mark.trace("REQ-WP-080")
def test_every_data_route_refuses_an_unsigned_request_and_returns_no_data() -> None:
    client = TestClient(_app(required=True))
    walked = _data_routes()

    for path, methods in walked:
        for method in sorted(methods & {"GET", "HEAD"}):
            response = client.request(method, _concrete(path))
            assert response.status_code == 401, (method, path, response.status_code)
            if method == "GET":
                assert response.json()["reason"] in REASONS
                assert set(response.json()) == {"reason"}, "the body must carry no market data"
    assert len(walked) > 0


@pytest.mark.trace("REQ-WP-080")
def test_a_signed_request_gets_exactly_what_an_unprotected_app_returns() -> None:
    protected = TestClient(_app(required=True))
    open_ = TestClient(_app(required=False))
    header = {"Authorization": f"tma {_signed()}"}

    for path, methods in _data_routes():
        if "GET" not in methods:
            continue
        mine = protected.get(_concrete(path), headers=header)
        theirs = open_.get(_concrete(path))
        assert mine.status_code != 401, path
        assert (mine.status_code, mine.content) == (theirs.status_code, theirs.content), path


@pytest.mark.trace("REQ-WP-080")
def test_with_authentication_off_nothing_changes_for_anyone() -> None:
    client = TestClient(_app(required=False))

    for path, methods in _data_routes():
        if "GET" in methods:
            assert client.get(_concrete(path)).status_code != 401, path


# --- what a header can be -------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize(
    "value",
    [
        "",
        "tma",
        "tma ",
        "Bearer " + "x" * 40,
        "tma " + "x" * 200_000,
        b"tma \xff\xfe\xfd",
        "tma auth_date=1&hash=zz",
    ],
    ids=[
        "empty",
        "scheme-only",
        "blank-payload",
        "other-scheme",
        "enormous",
        "not-utf8",
        "garbage",
    ],
)
def test_a_header_that_is_not_a_signed_launch_is_a_401_never_a_500(value: str | bytes) -> None:
    client = TestClient(_app(required=True), raise_server_exceptions=True)

    response = client.get("/api/v1/timeframes", headers={"Authorization": value})

    assert response.status_code == 401
    assert response.json()["reason"] in REASONS


@pytest.mark.trace("REQ-WP-080")
def test_a_stale_signed_launch_is_refused_at_the_gate_for_the_right_reason() -> None:
    client = TestClient(_app(required=True))

    response = client.get(
        "/api/v1/timeframes", headers={"Authorization": f"tma {_signed(NOW - MAX_AGE - 1)}"}
    )

    assert response.status_code == 401 and response.json() == {"reason": "too_old"}


# --- what is not behind it ------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-080")
def test_readiness_and_metrics_answer_without_a_launch() -> None:
    client = TestClient(_app(required=True))

    assert client.get("/readyz").status_code != 401
    assert client.get("/metrics").status_code != 401


@pytest.mark.trace("REQ-WP-080")
def test_the_websocket_is_refused_when_authentication_is_required() -> None:
    """A browser cannot send an Authorization header on a websocket, the page does not use it, and
    launch data in a URL would land in logs. So it is closed (1008), not authenticated."""
    with pytest.raises(WebSocketDisconnect) as closed:
        with TestClient(_app(required=True)).websocket_connect("/ws/market"):
            pass

    assert closed.value.code == 1008


@pytest.mark.trace("REQ-WP-080")
def test_the_websocket_still_works_with_authentication_off() -> None:
    with TestClient(_app(required=False)).websocket_connect("/ws/market") as socket:
        socket.send_text("not a subscription")
        assert socket.receive_json()["ok"] is False


# --- construction ---------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-080")
def test_a_gate_with_no_token_refuses_to_exist() -> None:
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        TelegramGate(bot_token="", max_age_seconds=MAX_AGE, clock=lambda: NOW)


@pytest.mark.trace("REQ-WP-080")
@pytest.mark.parametrize("scheme", ["Bearer", "Basic", "tma:", "TMA"])
def test_another_scheme_is_malformed_and_not_a_bad_signature(scheme: str) -> None:
    """Found by the mutation sweep: with the scheme check removed every one of these was still
    refused,
    only for a different reason, and no test pinned the reason."""
    client = TestClient(_app(required=True))

    response = client.get("/api/v1/timeframes", headers={"Authorization": f"{scheme} {_signed()}"})

    assert response.status_code == 401 and response.json() == {"reason": "malformed"}
