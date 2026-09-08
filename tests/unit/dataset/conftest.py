"""Snapshots, extrema and rows built by hand (REQ-WP-017)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dataset import FeatureSnapshot, Label, Row
from channelflow.extrema import ConfirmedExtremum

MINUTE_NS = 60 * 1_000_000_000
BASE_NS = 1788838800000000000
ENTITY = "binance:BTCUSDT:1m"


def snapshot(
    *,
    name: str = "qi_l1",
    at: int,
    value: float = 0.5,
    source_at: int | None = None,
    finalized: bool = True,
    entity: str = ENTITY,
) -> FeatureSnapshot:
    return FeatureSnapshot(
        entity=entity,
        as_of_ns=BASE_NS + at * MINUTE_NS,
        feature_name=name,
        feature_version=1,
        value=value,
        source_max_event_ns=BASE_NS + (at if source_at is None else source_at) * MINUTE_NS,
        from_finalized_bars=finalized,
    )


def extremum(
    *, at: int, known_at: int, kind: str = "HIGH", price: str = "110"
) -> ConfirmedExtremum:
    return ConfirmedExtremum.create(
        instrument_id="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        extremum_type=kind,
        extremum_time_ns=BASE_NS + at * MINUTE_NS,
        known_at_ns=BASE_NS + known_at * MINUTE_NS,
        price=Decimal(price),
        confirmation_method="directional_change",
        confirmation_lag_bars=known_at - at,
        reversal_bps=250.0,
        threshold_bps=200.0,
    )


def row(
    *,
    at: int,
    horizon: int = 10,
    available: int | None = None,
    label_class: str = "NO_TURN",
    extremum_at: int | None = None,
) -> Row:
    return Row(
        entity=ENTITY,
        as_of_ns=BASE_NS + at * MINUTE_NS,
        features={"qi_l1": 0.5},
        source_max_event_ns=BASE_NS + at * MINUTE_NS,
        label=Label(
            label_class=label_class,  # type: ignore[arg-type]
            horizon_end_ns=BASE_NS + (at + horizon) * MINUTE_NS,
            available_ns=BASE_NS
            + (available if available is not None else at + horizon) * MINUTE_NS,
            extremum_time_ns=None if extremum_at is None else BASE_NS + extremum_at * MINUTE_NS,
        ),
    )


@pytest.fixture
def clean_rows() -> list[Row]:
    """Sixty honest rows, ten minutes apart in horizon.

    Every fourth carries a turning-point label rather than a no-turn. Without
    them the `label_available_at_confirmation` check examines nothing, and a
    fixture that leaves a rule with zero rows to look at is exactly the silent
    non-coverage ADR-025 makes visible.
    """
    return [
        row(at=i) if i % 4 else row(at=i, label_class="MAX", extremum_at=i + 5, available=i + 8)
        for i in range(60)
    ]
