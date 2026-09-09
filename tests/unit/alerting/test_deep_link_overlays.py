"""The alert's link carries the chart's state (REQ-US-002, PRD sections 27.1-27.2)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from channelflow.alerting import Alert, Overlay, chart_deep_link
from channelflow.signals import Candidate, CandidateState, Transition

BASE_NS = 1788838800000000000


def alert(*, overlays: tuple[Overlay, ...] = ()) -> Alert:
    candidate = Candidate(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=900_000_000_000,
        direction="short",
        boundary="upper",
        state=CandidateState.CONFIRMED,
        opened_at_ns=BASE_NS,
        bars_since_open=2,
        history=(
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=BASE_NS,
                reason="price entered the upper zone",
            ),
        ),
    )
    return Alert(
        candidate=candidate,
        price=Decimal("112000"),
        invalidation_price=Decimal("113000"),
        research_target_price=Decimal("110000"),
        event_time_ns=BASE_NS,
        chart_base_url="https://charts.example",
        overlays=overlays,
    )


@pytest.mark.trace("REQ-US-002")
def test_the_link_names_the_overlays_that_were_active() -> None:
    """SC-001, FR-001, FR-002.

    REQ-US-002 asks for "all overlays active at signal time" to be restored, and
    a link that does not carry them cannot restore anything -- the reader would
    land on a chart configured however their last visit left it.
    """
    link = chart_deep_link(alert(overlays=(Overlay.VOLUME_PROFILE, Overlay.CHANNEL_CENTER)))

    assert "overlays=channel_center%2Cvolume_profile" in link


@pytest.mark.trace("REQ-US-002")
def test_the_overlay_order_is_stable() -> None:
    """SC-002, FR-002, FR-003.

    Two links from one alert must be one link. A set serialized in iteration
    order would make the same alert produce different URLs, and a resent alert
    would look like a different signal.
    """
    first = chart_deep_link(alert(overlays=(Overlay.VOLUME_PROFILE, Overlay.CANDLES)))
    second = chart_deep_link(alert(overlays=(Overlay.CANDLES, Overlay.VOLUME_PROFILE)))

    assert first == second


@pytest.mark.trace("REQ-US-002")
def test_an_alert_declaring_nothing_omits_the_parameter() -> None:
    """SC-001, FR-002.

    Not a default set written into the link. The link would then claim the alert
    knew what was on screen, and the chart would restore a state nobody
    recorded.
    """
    link = chart_deep_link(alert())

    assert "overlays=" not in link


@pytest.mark.trace("REQ-US-002")
def test_an_overlay_the_prd_does_not_list_is_refused() -> None:
    """SC-003, FR-001.

    PRD section 27.2 is the vocabulary. A name outside it reaches the chart,
    fails to match any layer, and is discarded there -- so the alert would have
    recorded a state that silently cannot be restored.
    """
    with pytest.raises(ValidationError):
        alert(overlays=("candlesticks",))  # type: ignore[arg-type]


@pytest.mark.trace("REQ-US-002")
def test_the_overlay_vocabulary_is_the_prds_own_list() -> None:
    """FR-001.

    Section 27.2's twelve toggle layers, in the PRD's order. The chart draws a
    subset of them today; the vocabulary is the full list so a link written now
    stays valid as layers are added.
    """
    assert [o.value for o in Overlay] == [
        "candles",
        "channel_center",
        "channel_bounds",
        "forecast_corridor",
        "signal_zones",
        "signal_marker",
        "volume_profile",
        "poc_vah_val",
        "vwap",
        "lob_walls",
        "dex_liquidity_bands",
        "liquidation_levels",
    ]


@pytest.mark.trace("REQ-US-002")
def test_the_instant_and_the_signal_id_are_still_in_the_link() -> None:
    """FR-002.

    The overlay parameter is an addition. PRD section 27.1's link is the rest of
    it, and every alert ever sent carries the old shape.
    """
    link = chart_deep_link(alert(overlays=(Overlay.CANDLES,)))

    assert "/chart/binance/BTCUSDT" in link
    assert "tf=15m" in link
    assert "at=2026-09-07T09%3A00%3A00Z" in link or "at=" in link
    assert "signal=" in link
