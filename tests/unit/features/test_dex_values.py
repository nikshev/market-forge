"""The two DEX features as of a bar's close, from stored swaps and pool readings (REQ-WP-099)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dex.hyperevm_collect import POLL_INTERVAL_S
from channelflow.features.dex import LiquidityReading
from channelflow.features.dex_values import (
    DEX_FEATURES,
    LIQUIDITY_STALENESS_NS,
    WINDOW_NS,
    StoredSwap,
    dex_values,
)

pytestmark = pytest.mark.trace("REQ-WP-099")

SECOND = 1_000_000_000
MINUTE = 60 * SECOND
CLOSE = 1_800_000_000 * SECOND  # a minute boundary
A, B, LIQ = "0xa", "0xb", "0xa"


def swap(at: int, amount0: str, *, ingest: int | None = None, pool: str = A) -> StoredSwap:
    return StoredSwap(
        pool=pool,
        event_time_ns=at,
        ingest_time_ns=at + SECOND if ingest is None else ingest,
        amount0=Decimal(amount0),
    )


def listening(pool: str, *, close: int = CLOSE, minutes: int = 5, per_minute: int = 2):
    """Readings every `60/per_minute` seconds through `close` -- the collector was there."""
    step = MINUTE // per_minute
    return [
        LiquidityReading(
            state_time_ns=close - i * step, active_liquidity=1_000 + i, quality="partial_ticks"
        )
        for i in range(minutes * per_minute)
    ][::-1]


def both_listening(close: int = CLOSE) -> dict[str, list[LiquidityReading]]:
    return {A: listening(A, close=close), B: listening(B, close=close)}


def values(swaps: list[StoredSwap], states: dict[str, list[LiquidityReading]], close: int = CLOSE):
    return dex_values(swaps, states, close_ns=close, pools=(A, B), liquidity_pool=LIQ)


def test_the_features_are_the_two_the_registry_names() -> None:
    assert DEX_FEATURES == ("dex_swap_imbalance", "dex_active_liquidity")


def test_the_window_is_five_minutes_and_staleness_is_three_polls() -> None:
    assert WINDOW_NS == 5 * MINUTE
    assert LIQUIDITY_STALENESS_NS == 3 * POLL_INTERVAL_S * SECOND


def test_the_imbalance_is_net_flow_over_gross_flow_across_both_pools() -> None:
    got = values(
        [swap(CLOSE - 4 * MINUTE, "3"), swap(CLOSE - 2 * MINUTE, "-1", pool=B)], both_listening()
    )

    assert got["dex_swap_imbalance"] == pytest.approx(0.5)


def test_a_swap_stored_after_the_close_is_not_in_that_closes_value() -> None:
    # Dated before the close, stored 10 s after it: nobody could have known it at the close.
    late = swap(CLOSE - 5 * SECOND, "-5", ingest=CLOSE + 10 * SECOND)

    got = values([swap(CLOSE - 2 * MINUTE, "1"), late], both_listening())

    assert got["dex_swap_imbalance"] == pytest.approx(1.0)


def test_a_swap_dated_after_the_close_is_not_in_it_even_if_stored_early() -> None:
    early = swap(CLOSE + 5 * SECOND, "-5", ingest=CLOSE - SECOND)

    got = values([swap(CLOSE - 2 * MINUTE, "1"), early], both_listening())

    assert got["dex_swap_imbalance"] == pytest.approx(1.0)


def test_the_window_is_open_at_its_floor_and_closed_at_the_close() -> None:
    on_floor = swap(CLOSE - WINDOW_NS, "-9")
    at_close = swap(CLOSE, "1", ingest=CLOSE)

    got = values([on_floor, at_close], both_listening())

    assert got["dex_swap_imbalance"] == pytest.approx(1.0)


def test_a_window_with_no_swap_has_no_imbalance_not_zero() -> None:
    got = values([], both_listening())

    assert "dex_swap_imbalance" not in got


def test_a_window_the_collector_did_not_cover_has_no_imbalance_even_with_swaps_in_it() -> None:
    # One minute without a reading from pool B: the swaps seen are not all the swaps there were.
    gap = [
        r for r in listening(B) if not (CLOSE - 3 * MINUTE < r.state_time_ns <= CLOSE - 2 * MINUTE)
    ]

    got = values([swap(CLOSE - MINUTE, "1")], {A: listening(A), B: gap})

    assert "dex_swap_imbalance" not in got


def test_a_pool_nobody_read_leaves_the_window_uncovered() -> None:
    got = values([swap(CLOSE - MINUTE, "1")], {A: listening(A), B: []})

    assert "dex_swap_imbalance" not in got


def test_the_imbalance_never_reads_a_reading_from_after_the_close_as_coverage() -> None:
    after = [
        LiquidityReading(
            state_time_ns=CLOSE + i * SECOND, active_liquidity=1, quality="partial_ticks"
        )
        for i in range(1, 400)
    ]

    got = values([swap(CLOSE - MINUTE, "1")], {A: after, B: after})

    assert got == {}


def test_the_active_liquidity_is_the_liquidity_pools_latest_reading_at_or_before_the_close() -> (
    None
):
    states = both_listening()
    expected = max(states[A], key=lambda r: r.state_time_ns).active_liquidity

    got = values([], states)

    assert got["dex_active_liquidity"] == float(expected)


def test_the_other_pools_liquidity_is_not_the_one_shown() -> None:
    states = both_listening()
    states[B] = [LiquidityReading(r.state_time_ns, 7_000_000, "partial_ticks") for r in states[B]]

    assert values([], states)["dex_active_liquidity"] != 7_000_000.0


def test_a_reading_older_than_three_polls_is_not_the_liquidity_now() -> None:
    stale = [LiquidityReading(CLOSE - LIQUIDITY_STALENESS_NS - SECOND, 5, "partial_ticks")]

    got = values([], {A: stale, B: stale})

    assert "dex_active_liquidity" not in got


def test_a_reading_exactly_three_polls_old_still_counts() -> None:
    edge = [LiquidityReading(CLOSE - LIQUIDITY_STALENESS_NS, 5, "partial_ticks")]

    assert values([], {A: edge, B: edge})["dex_active_liquidity"] == 5.0


def test_a_reading_of_a_grade_that_cannot_carry_liquidity_is_ignored() -> None:
    diverged = [LiquidityReading(CLOSE - SECOND, 5, "diverged")]

    assert "dex_active_liquidity" not in values([], {A: diverged, B: diverged})


def test_liquidity_does_not_need_a_covered_window() -> None:
    one = [LiquidityReading(CLOSE - 10 * SECOND, 42, "partial_ticks")]

    got = values([swap(CLOSE - MINUTE, "1")], {A: one, B: []})

    assert got == {"dex_active_liquidity": 42.0}
