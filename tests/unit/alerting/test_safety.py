"""The rules that hold across the package (REQ-WP-008).

PRD section 25.6 lists six alert-quality metrics and gives exactly one of them
a required value: "stale-data alert count — must be zero". That is the only
number in the document specified as an absolute, so it is treated as one here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.alerting import Alert, AlertGate, Dispatcher
from channelflow.book import BookHealth
from channelflow.signals import Candidate

from .conftest import BASE_NS, MINUTE_NS

CHART_BASE = "https://charts.example.internal"
TOLERANCE_NS = 5 * 1_000_000_000


@dataclass
class FakeTransport:
    sent: list[str] = field(default_factory=list)

    def send(self, text: str, *, link: str) -> str:
        self.sent.append(text)
        return "ok"


def _alert(candidate: Candidate) -> Alert:
    return Alert(
        candidate=candidate,
        price=Decimal("112480"),
        invalidation_price=Decimal("113080"),
        research_target_price=Decimal("111900"),
        event_time_ns=BASE_NS + 3 * MINUTE_NS,
        chart_base_url=CHART_BASE,
    )


def _gate(transport: FakeTransport) -> tuple[AlertGate, Dispatcher]:
    dispatcher = Dispatcher(transport=transport)
    return AlertGate(dispatcher=dispatcher, staleness_tolerance_ns=TOLERANCE_NS), dispatcher


@pytest.mark.trace("REQ-WP-008")
def test_a_fresh_book_lets_the_alert_through(candidate: Candidate) -> None:
    transport = FakeTransport()
    gate, dispatcher = _gate(transport)

    gate.offer(
        _alert(candidate),
        health=BookHealth(valid=True, gap_count=0, last_sequence=10, stale_ns=0),
        at_ns=BASE_NS,
    )

    assert len(transport.sent) == 1
    assert dispatcher.audit[0].status == "delivered"


@pytest.mark.trace("REQ-WP-008")
def test_a_stale_book_suppresses_the_alert(candidate: Candidate) -> None:
    """SC-008, FR-015. PRD section 25.6: stale-data alerts must be zero.

    A setup computed from a book that stopped updating describes a market that
    may have moved. Sending it anyway is worse than silence, because the reader
    cannot tell the two apart.
    """
    transport = FakeTransport()
    gate, dispatcher = _gate(transport)

    gate.offer(
        _alert(candidate),
        health=BookHealth(valid=True, gap_count=0, last_sequence=10, stale_ns=TOLERANCE_NS + 1),
        at_ns=BASE_NS,
    )

    assert transport.sent == []
    assert dispatcher.audit[0].status == "suppressed"
    assert "stale" in dispatcher.audit[0].reason


@pytest.mark.trace("REQ-WP-008")
def test_an_invalid_book_suppresses_the_alert(candidate: Candidate) -> None:
    """FR-015. A book that has diverged is not stale, it is wrong -- and PRD
    section 11.1 rule 6 already forbids emitting anything from it."""
    transport = FakeTransport()
    gate, dispatcher = _gate(transport)

    gate.offer(
        _alert(candidate),
        health=BookHealth(valid=False, gap_count=1, last_sequence=10, stale_ns=0),
        at_ns=BASE_NS,
    )

    assert transport.sent == []
    assert dispatcher.audit[0].status == "suppressed"
    assert "gap" in dispatcher.audit[0].reason or "invalid" in dispatcher.audit[0].reason


@pytest.mark.trace("REQ-WP-008")
def test_a_suppression_is_visible_in_the_audit(candidate: Candidate) -> None:
    """SC-008, the spec's third US5 scenario.

    A silent drop is indistinguishable from there having been no setup, and the
    difference matters to anyone asking why they heard nothing all morning.
    """
    transport = FakeTransport()
    gate, dispatcher = _gate(transport)

    gate.offer(
        _alert(candidate),
        health=BookHealth(valid=False, gap_count=3, last_sequence=10, stale_ns=0),
        at_ns=BASE_NS,
    )

    assert len(dispatcher.audit) == 1
    record = dispatcher.audit[0]
    assert record.signal_id == _alert(candidate).signal_id
    assert record.queued_at_ns == BASE_NS
    assert record.attempts == (), "a suppressed alert was never attempted"


@pytest.mark.trace("REQ-WP-008")
def test_the_tolerance_is_configurable(candidate: Candidate) -> None:
    """Principle X. What counts as stale depends on the timeframe being traded."""
    transport = FakeTransport()
    lenient = AlertGate(
        dispatcher=Dispatcher(transport=transport),
        staleness_tolerance_ns=60 * 1_000_000_000,
    )

    lenient.offer(
        _alert(candidate),
        health=BookHealth(valid=True, gap_count=0, last_sequence=10, stale_ns=TOLERANCE_NS + 1),
        at_ns=BASE_NS,
    )

    assert len(transport.sent) == 1


@pytest.mark.trace("REQ-WP-008")
def test_the_alerting_package_has_no_clock_and_no_http_client() -> None:
    """SC-009, FR-016, ADR-018.

    Asserted over the source. A clock would make a replayed stream produce a
    different audit; an HTTP client would put a credential and a blocking call
    into the path PRD section 26.4 says must never block.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "alerting"
    modules = list(package.glob("*.py"))
    assert modules, "the alerting package has no modules; this would pass vacuously"

    for module in modules:
        source = module.read_text()
        for forbidden in ("time.time", "datetime.now", "utcnow", "monotonic", "time.sleep"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
        for forbidden in ("import requests", "import httpx", "import urllib.request", "aiohttp"):
            assert forbidden not in source, f"{module.name} opens a socket: {forbidden!r}"


@pytest.mark.trace("REQ-WP-008")
def test_no_credential_appears_in_the_package_or_in_a_message(
    candidate: Candidate,
) -> None:
    """FR-017. The token lives in the caller's environment and nowhere else."""
    from channelflow.alerting import render_message

    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "alerting"
    for module in package.glob("*.py"):
        source = module.read_text().lower()
        for forbidden in ("bot_token", "api.telegram.org", "bot1", "getenv", "environ"):
            assert forbidden not in source, f"{module.name} mentions a credential: {forbidden!r}"

    message = render_message(_alert(candidate))
    assert "token" not in message.lower()
