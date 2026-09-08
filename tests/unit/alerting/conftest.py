"""A confirmed candidate and the context an alert is built from (REQ-WP-008)."""

from __future__ import annotations

import pytest

from channelflow.channels import ChannelQuality, ChannelSnapshot
from channelflow.signals import Candidate, CandidateState, Transition

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1788838800000000000  # a minute boundary


def transition(
    from_state: CandidateState, to_state: CandidateState, *, at_ns: int, reason: str
) -> Transition:
    return Transition(
        from_state=from_state, to_state=to_state, bar_close_time_ns=at_ns, reason=reason
    )


def confirmed_candidate(*, opened_at_ns: int = BASE_NS) -> Candidate:
    """The full happy path: approach, touch, rejection, confirmation."""
    steps = (
        (CandidateState.NONE, CandidateState.APPROACH, "price entered the upper zone"),
        (CandidateState.APPROACH, CandidateState.TOUCH, "reached the upper boundary"),
        (CandidateState.TOUCH, CandidateState.REJECTION_PENDING, "rejected by close_back_inside"),
        (
            CandidateState.REJECTION_PENDING,
            CandidateState.CONFIRMED,
            "rejection held for a second bar",
        ),
    )
    history = tuple(
        transition(a, b, at_ns=opened_at_ns + i * MINUTE_NS, reason=reason)
        for i, (a, b, reason) in enumerate(steps)
    )
    return Candidate(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=15 * MINUTE_NS,
        direction="short",
        boundary="upper",
        state=CandidateState.CONFIRMED,
        opened_at_ns=opened_at_ns,
        bars_since_open=3,
        history=history,
    )


@pytest.fixture
def candidate() -> Candidate:
    return confirmed_candidate()


@pytest.fixture
def channel() -> ChannelSnapshot:
    return ChannelSnapshot(
        as_of_ns=BASE_NS + 3 * MINUTE_NS,
        model_name="rolling_ols_log_price",
        model_version="1.0.0",
        lookback=60,
        center_now=112000.0,
        upper_now=113000.0,
        lower_now=111000.0,
        slope_normalized=-0.0037,
        width_pct=0.024,
        quality=ChannelQuality(
            score=0.83,
            submetrics={"r_squared": 0.9, "residual_stability": 0.8},
            contributing=("r_squared", "residual_stability"),
            unavailable=("forecast_calibration", "regime_compatibility", "age"),
        ),
        source_max_event_time_ns=BASE_NS + 3 * MINUTE_NS,
    )
