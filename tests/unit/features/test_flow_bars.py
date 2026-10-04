"""CVD and the trade-imbalance features, derived from the bars' stored aggressor split (REQ-WP-088).

Every expected value is arithmetic done by hand. The bars carry the buy/sell split in **base units**
(ADR-068), a trade count and the first and last trade id; a run is a stretch of consecutive
bars with no missing bar and no detectable missed trade, and CVD is a running sum within one.
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from channelflow.bars.models import Bar
from channelflow.features.flow_bars import FLOW_FEATURES, flow_rows

MINUTE_NS = 60_000_000_000
BASE_NS = 1_789_344_000_000_000_000


def make_bar(
    index: int,
    buy: str,
    sell: str,
    *,
    ids: tuple[int, int] | None = None,
    trade_count: int | None = None,
    is_final: bool = True,
    timeframe_ns: int = MINUTE_NS,
) -> Bar:
    first, last = ids if ids is not None else (index * 10 + 1, index * 10 + 10)
    count = trade_count if trade_count is not None else last - first + 1
    open_time = BASE_NS + index * timeframe_ns
    buy_d, sell_d = Decimal(buy), Decimal(sell)
    price = Decimal("100")
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=timeframe_ns,
        open_time_ns=open_time,
        close_time_ns=open_time + timeframe_ns,
        open=price,
        high=price,
        low=price,
        close=price,
        volume_base=buy_d + sell_d,
        volume_quote=(buy_d + sell_d) * price,
        trade_count=count,
        aggressive_buy_base=buy_d,
        aggressive_sell_base=sell_d,
        delta_base=buy_d - sell_d,
        vwap=price,
        high_time_ns=open_time,
        low_time_ns=open_time,
        first_trade_id=str(first),
        last_trade_id=str(last),
        is_final=is_final,
    )


def values(rows, name):
    return [row.values.get(name) for row in rows]


@pytest.mark.trace("REQ-WP-088")
def test_delta_and_cvd_are_hand_computed_for_three_bars() -> None:
    """SC-001. Buy/sell volumes (10,4), (6,6), (2,8): delta 6, 0, -6; CVD 6, 6, 0."""
    bars = [make_bar(0, "10", "4"), make_bar(1, "6", "6"), make_bar(2, "2", "8")]

    rows = flow_rows(bars, sequential_ids=True)

    assert values(rows, "delta_base") == [6.0, 0.0, -6.0]
    assert values(rows, "cvd_base") == [6.0, 6.0, 0.0]
    assert [row.at_ns for row in rows] == [bar.close_time_ns for bar in bars]


@pytest.mark.trace("REQ-WP-088")
def test_normalized_delta_is_the_delta_over_the_bars_volume() -> None:
    rows = flow_rows([make_bar(0, "10", "4"), make_bar(1, "6", "6")], sequential_ids=True)

    assert values(rows, "normalized_delta_base") == [pytest.approx(6 / 14), pytest.approx(0.0)]


@pytest.mark.trace("REQ-WP-088")
def test_a_bar_where_nothing_traded_has_no_normalized_delta_and_is_not_a_break() -> None:
    """Zero volume is not a zero ratio: it is no ratio. And a quiet bar is not a missed trade."""
    bars = [
        make_bar(0, "5", "0"),
        make_bar(1, "0", "0", ids=(11, 10), trade_count=0),
        make_bar(2, "3", "0", ids=(11, 20)),
    ]

    rows = flow_rows(bars, sequential_ids=True)

    assert "normalized_delta_base" not in rows[1].values
    assert values(rows, "cvd_base") == [5.0, 5.0, 8.0]
    assert values(rows, "cvd_run") == [0.0, 0.0, 0.0]


@pytest.mark.trace("REQ-WP-088")
def test_slope_is_delta_over_seconds_and_acceleration_is_absent_in_a_runs_first_bar() -> None:
    rows = flow_rows([make_bar(0, "10", "4"), make_bar(1, "6", "6")], sequential_ids=True)

    assert values(rows, "cvd_base_slope") == [pytest.approx(6 / 60), pytest.approx(0.0)]
    assert "cvd_base_acceleration" not in rows[0].values
    assert rows[1].values["cvd_base_acceleration"] == pytest.approx((0.0 - 6 / 60) / 60)


@pytest.mark.trace("REQ-WP-088")
def test_a_forming_bar_produces_no_row() -> None:
    rows = flow_rows(
        [make_bar(0, "10", "4"), make_bar(1, "9", "1", is_final=False)], sequential_ids=True
    )

    assert len(rows) == 1


@pytest.mark.trace("REQ-WP-088")
def test_the_order_the_bars_arrive_in_does_not_matter() -> None:
    bars = [make_bar(i, str(i + 3), str(7 - i)) for i in range(6)]
    shuffled = list(bars)
    random.Random(7).shuffle(shuffled)

    assert flow_rows(shuffled, sequential_ids=True) == flow_rows(bars, sequential_ids=True)


@pytest.mark.trace("REQ-WP-088")
def test_appending_later_bars_leaves_the_earlier_rows_unchanged() -> None:
    """SC-002, Principle I: a row at t depends only on bars at or before t."""
    bars = [make_bar(i, str(i + 3), str(7 - i)) for i in range(8)]

    early = flow_rows(bars[:4], sequential_ids=True)
    later = flow_rows(bars, sequential_ids=True)

    assert later[:4] == early


@pytest.mark.trace("REQ-WP-088")
def test_a_missing_bar_ends_the_run_and_nothing_is_summed_across_it() -> None:
    """SC-003. Three bars with the middle one removed: two runs, no CVD across the gap."""
    bars = [make_bar(0, "10", "4"), make_bar(1, "6", "6"), make_bar(3, "2", "8", ids=(31, 40))]

    rows = flow_rows(bars, sequential_ids=True)

    assert values(rows, "cvd_run") == [0.0, 0.0, 1.0]
    assert values(rows, "cvd_base") == [6.0, 6.0, -6.0]


@pytest.mark.trace("REQ-WP-088")
def test_a_trade_id_jump_between_bars_ends_the_run_for_a_sequential_venue() -> None:
    bars = [
        make_bar(0, "10", "4"),
        make_bar(1, "6", "6", ids=(11, 20)),
        make_bar(2, "2", "8", ids=(25, 34)),
    ]

    rows = flow_rows(bars, sequential_ids=True)

    assert values(rows, "cvd_run") == [0.0, 0.0, 1.0]
    assert values(rows, "cvd_base")[2] == -6.0


@pytest.mark.trace("REQ-WP-088")
def test_a_bar_whose_id_span_differs_from_its_trade_count_has_no_row_and_breaks_both_sides() -> (
    None
):
    """Ids 11..20 is ten trades; a count of 7 means three were missed, so the delta is wrong."""
    bars = [
        make_bar(0, "10", "4"),
        make_bar(1, "6", "6", ids=(11, 20), trade_count=7),
        make_bar(2, "2", "8", ids=(21, 30)),
    ]

    rows = flow_rows(bars, sequential_ids=True)

    assert [row.at_ns for row in rows] == [bars[0].close_time_ns, bars[2].close_time_ns]
    assert values(rows, "cvd_run") == [0.0, 1.0]
    assert values(rows, "cvd_base")[1] == -6.0, "the sum starts again after the incomplete bar"


@pytest.mark.trace("REQ-WP-088")
def test_a_venue_without_sequential_ids_breaks_only_on_a_missing_bar() -> None:
    jump = [
        make_bar(0, "10", "4"),
        make_bar(1, "6", "6", ids=(11, 20)),
        make_bar(2, "2", "8", ids=(900, 905)),
    ]
    gap = [make_bar(0, "10", "4"), make_bar(2, "6", "6", ids=(21, 30))]

    assert values(flow_rows(jump, sequential_ids=False), "cvd_run") == [0.0, 0.0, 0.0]
    assert values(flow_rows(gap, sequential_ids=False), "cvd_run") == [0.0, 1.0]


@pytest.mark.trace("REQ-WP-088")
def test_each_timeframe_has_its_own_runs() -> None:
    """A 15m bar's stored ids and counts are sums over its minutes, so the same checks apply."""
    quarter = 15 * MINUTE_NS
    bars = [
        make_bar(0, "100", "40", ids=(1, 150), timeframe_ns=quarter),
        make_bar(1, "60", "60", ids=(151, 300), timeframe_ns=quarter),
    ]

    rows = flow_rows(bars, sequential_ids=True)

    assert values(rows, "cvd_base") == [60.0, 60.0]
    assert values(rows, "cvd_base_slope") == [pytest.approx(60 / 900), pytest.approx(0.0)]


@pytest.mark.trace("REQ-WP-088")
def test_the_feature_names_are_the_six_base_names_and_never_the_notional_ones() -> None:
    assert set(FLOW_FEATURES) == {
        "delta_base",
        "cvd_base",
        "normalized_delta_base",
        "cvd_base_slope",
        "cvd_base_acceleration",
        "cvd_run",
    }
    assert "cvd" not in FLOW_FEATURES and "delta_notional" not in FLOW_FEATURES


@pytest.mark.trace("REQ-WP-088")
def test_no_bars_give_no_rows() -> None:
    assert flow_rows([], sequential_ids=True) == []


@pytest.mark.trace("REQ-WP-088")
def test_the_first_bar_of_a_new_run_has_no_acceleration_either() -> None:
    """A slope from before the break is not the previous slope of a run that has just begun."""
    bars = [
        make_bar(0, "10", "4"),
        make_bar(1, "6", "6"),
        make_bar(3, "2", "8", ids=(31, 40)),
        make_bar(4, "5", "5", ids=(41, 50)),
    ]

    rows = flow_rows(bars, sequential_ids=True)

    assert "cvd_base_acceleration" in rows[1].values
    assert "cvd_base_acceleration" not in rows[2].values
    assert "cvd_base_acceleration" in rows[3].values
