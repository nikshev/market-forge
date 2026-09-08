"""The message a reader actually sees (REQ-WP-008).

PRD section 26.1 gives the layout; ADR-016 says which of its blocks can exist
today and that the rest are absent rather than placeheld.

The whole message is compared against one literal string. Asserting field by
field passes a renderer whose output is unreadable, and layout is most of what
a message is for -- someone scanning a dozen alerts on a phone reads the shape
before the numbers.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.alerting import Alert, OrderFlowSummary, render_message, signal_id_for
from channelflow.channels import ChannelSnapshot
from channelflow.signals import Candidate

from .conftest import BASE_NS, MINUTE_NS, confirmed_candidate

CHART_BASE = "https://charts.example.internal"


def _alert(
    candidate: Candidate,
    channel: ChannelSnapshot | None = None,
    flow: OrderFlowSummary | None = None,
) -> Alert:
    return Alert(
        candidate=candidate,
        channel=channel,
        order_flow=flow,
        price=Decimal("112480"),
        invalidation_price=Decimal("113080"),
        research_target_price=Decimal("111900"),
        event_time_ns=BASE_NS + 3 * MINUTE_NS,
        chart_base_url=CHART_BASE,
    )


# --- the signal id (ADR-017) ---


@pytest.mark.trace("REQ-WP-008")
def test_the_signal_id_is_the_same_for_the_same_candidate(candidate: Candidate) -> None:
    """FR-014, SC-007. The property a random UUID would quietly break."""
    assert signal_id_for(candidate) == signal_id_for(confirmed_candidate())


@pytest.mark.trace("REQ-WP-008")
def test_the_signal_id_differs_for_a_different_candidate(candidate: Candidate) -> None:
    """Guard on the guard: a constant id would satisfy the test above."""
    later = confirmed_candidate(opened_at_ns=BASE_NS + 15 * MINUTE_NS)

    assert signal_id_for(candidate) != signal_id_for(later)


@pytest.mark.trace("REQ-WP-008")
def test_the_signal_id_is_uuid_shaped(candidate: Candidate) -> None:
    """PRD section 27.1's deep link carries `signal=<uuid>`."""
    from uuid import UUID

    assert UUID(str(signal_id_for(candidate)))


# --- the message ---


@pytest.mark.trace("REQ-WP-008")
def test_the_full_message_matches_expected_output(
    candidate: Candidate, channel: ChannelSnapshot
) -> None:
    """SC-001. One literal, so a layout regression is a failing test."""
    flow = OrderFlowSummary(
        ofi_30s="bearish",
        depth_imbalance_25bps=-0.31,
        wall_persistence="high",
    )
    expected = "\n".join(
        [
            "🔴 BTCUSDT — SHORT SETUP",
            "",
            "Venue: binance",
            "TF: 15m",
            "Price: 112,480",
            "Time: 2026-09-08 03:43 UTC",
            "",
            "Setup: Upper Channel Rejection",
            "",
            "Channel",
            "Direction: DOWN",
            "Slope: -0.37% / lookback",
            "Width: 2.4%",
            "Position: 0.74",
            "Quality: 0.83",
            "",
            "Order Flow",
            "OFI 30s: bearish",
            "Depth imbalance 25bps: -0.31",
            "Ask-wall persistence: high",
            "",
            "Invalidation: 113,080",
            "Research target: 111,900",
        ]
    )

    assert render_message(_alert(candidate, channel, flow)) == expected


@pytest.mark.trace("REQ-WP-008")
def test_a_section_with_no_data_is_absent_by_heading(candidate: Candidate) -> None:
    """SC-002, FR-004, ADR-016.

    Asserted on the heading rather than on the values: a renderer that emitted
    "Order Flow" followed by nothing would pass a test that only looked for the
    numbers, and would read on a phone as a section that failed to load.
    """
    lines = render_message(_alert(candidate)).splitlines()

    # A whole line, not a substring: "Channel" also occurs inside the setup
    # name "Upper Channel Rejection", and a substring check there would pass
    # for the wrong reason -- or fail for one, as this test first did.
    assert "Order Flow" not in lines
    assert "Channel" not in lines
    assert any("BTCUSDT" in line for line in lines), "the message must still say what it is about"


@pytest.mark.trace("REQ-WP-008")
def test_no_placeholder_is_substituted_for_a_missing_block(candidate: Candidate) -> None:
    """ADR-016's actual claim. `Score: —` beside `Score: 82/100` is a
    formatting difference to a reader scanning quickly."""
    message = render_message(_alert(candidate, None, None))

    for absent in ("Score", "Model probability", "Derivatives", "DeFi"):
        assert absent not in message
    for placeholder in ("N/A", "n/a", "—:", "None", "null"):
        assert placeholder not in message


@pytest.mark.trace("REQ-WP-008")
def test_rendering_is_deterministic(candidate: Candidate, channel: ChannelSnapshot) -> None:
    """FR-005. The property that makes the literal above testable at all."""
    alert = _alert(candidate, channel)

    assert render_message(alert) == render_message(alert)


# --- the deep link (US4) ---


@pytest.mark.trace("REQ-WP-008")
def test_the_deep_link_follows_the_documented_format(
    candidate: Candidate,
) -> None:
    """SC-007, FR-013. PRD section 27.1:
    `/chart/:venue/:symbol?tf=15m&at=<iso>&signal=<uuid>`."""
    from channelflow.alerting import chart_deep_link

    link = chart_deep_link(_alert(candidate))

    assert link.startswith(f"{CHART_BASE}/chart/binance/BTCUSDT?")
    assert "tf=15m" in link
    assert "at=2026-09-08T03%3A43%3A00Z" in link or "at=2026-09-08T03:43:00Z" in link
    assert f"signal={signal_id_for(candidate)}" in link


@pytest.mark.trace("REQ-WP-008")
def test_the_chart_host_is_configured_not_hard_coded(candidate: Candidate) -> None:
    """FR-013. A hard-coded host would work in exactly one deployment."""
    from channelflow.alerting import chart_deep_link

    alert = _alert(candidate).model_copy(update={"chart_base_url": "https://other.example"})

    assert chart_deep_link(alert).startswith("https://other.example/chart/")


@pytest.mark.trace("REQ-WP-008")
def test_an_alert_without_a_chart_base_is_refused(candidate: Candidate) -> None:
    """The spec's fourth edge case: fail at construction rather than send a
    message whose only actionable element is broken."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Alert(
            candidate=candidate,
            channel=None,
            order_flow=None,
            price=Decimal("112480"),
            invalidation_price=Decimal("113080"),
            research_target_price=Decimal("111900"),
            event_time_ns=BASE_NS,
            chart_base_url="",
        )
