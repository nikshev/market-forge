"""The venue basis is found in time proportional to the bars, not to bars times quotes (REQ-WP-107).

`GET /features/timeseries` merges the venue basis into the series. For each bar of the answer it
scanned every quote the table held, so a day of one-minute bars against three days of quotes was
tens of millions of comparisons: on 2026-10-13 the repository answered in 0.75 s and the HTTP
request took 3.8 s, and the difference was this. What is answered is unchanged and pinned here,
including which quote wins a tie.
"""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

from channelflow.api.repositories import select_venue_basis

pytestmark = pytest.mark.trace("REQ-WP-107")

MINUTE = 60_000_000_000
T0 = 1_789_344_000_000_000_000


def consensus(minute: int, mid: str = "100", *, asset: str = "BTCUSDT") -> dict[str, object]:
    return {
        "asset": asset,
        "market_type": "perp",
        "bar_close_ns": T0 + minute * MINUTE,
        "consensus_mid": Decimal(mid),
        "venue_count": 2,
        "refusal_reason": None,
    }


def quote(
    minute: float, mid: str, *, venue: str = "bybit", symbol: str = "BTCUSDT"
) -> dict[str, object]:
    return {
        "venue": venue,
        "symbol": symbol,
        "ts_ns": T0 + int(minute * MINUTE),
        "ingest_ns": 0,
        "bid": Decimal(mid),
        "ask": Decimal(mid),
        "mid": Decimal(mid),
    }


def basis(consensus_rows, quote_rows, **kw):  # type: ignore[no-untyped-def]
    return select_venue_basis(
        consensus_rows,
        quote_rows,
        asset="BTCUSDT",
        market_type="perp",
        venue="bybit",
        start_ns=kw.get("start_ns", T0),
        end_ns=kw.get("end_ns", T0 + 10_000 * MINUTE),
    )


def test_the_newest_quote_at_or_before_the_close_is_the_one_used() -> None:
    got = basis([consensus(10)], [quote(3, "90"), quote(9.5, "110"), quote(10.5, "999")])

    assert [float(p["venue_basis_bps"]) for p in got] == [pytest.approx(1000.0)]  # 110 vs 100


def test_a_quote_exactly_at_the_close_is_available_at_it() -> None:
    got = basis([consensus(10)], [quote(9, "90"), quote(10, "105")])

    assert float(got[0]["venue_basis_bps"]) == pytest.approx(500.0)


def test_of_two_quotes_with_the_same_exchange_time_the_first_stored_wins() -> None:
    """What `max` over the rows in table order has always picked."""
    got = basis([consensus(10)], [quote(9, "101"), quote(9, "150"), quote(2, "80")])

    assert float(got[0]["venue_basis_bps"]) == pytest.approx(100.0)


def test_another_venue_or_symbol_is_not_this_ones_quote() -> None:
    quotes = [quote(9, "500", venue="okx"), quote(9, "500", symbol="ETHUSDT"), quote(8, "100")]

    got = basis([consensus(10)], quotes)

    assert float(got[0]["venue_basis_bps"]) == pytest.approx(0.0)


def test_a_bar_with_no_quote_at_or_before_it_is_skipped_not_zero() -> None:
    assert basis([consensus(1)], [quote(5, "100")]) == []


def test_the_quotes_may_arrive_in_any_order() -> None:
    forward = basis([consensus(10)], [quote(1, "90"), quote(9, "110")])
    backward = basis([consensus(10)], [quote(9, "110"), quote(1, "90")])

    assert forward == backward


def test_a_refused_consensus_and_other_assets_are_skipped_as_before() -> None:
    refused = {**consensus(10), "consensus_mid": None}

    got = basis([refused, consensus(11, asset="ETHUSDT"), consensus(12)], [quote(5, "100")])

    assert [p["bar_close_ns"] for p in got] == [T0 + 12 * MINUTE]


def test_a_day_of_bars_against_days_of_quotes_is_not_a_second_of_work() -> None:
    bars = [consensus(m) for m in range(0, 1440)]
    quotes = [quote(m, "100") for m in range(0, 1440 * 3)] + [
        quote(m, "100", venue="okx") for m in range(0, 1440 * 3)
    ]

    started = time.perf_counter()
    got = basis(bars, quotes, end_ns=T0 + 1440 * MINUTE)
    elapsed = time.perf_counter() - started

    assert len(got) == 1440
    assert elapsed < 1.0, f"{elapsed:.2f}s for 1,440 bars against {len(quotes)} quotes"


def test_shuffled_quotes_give_the_answer_that_ordered_quotes_give() -> None:
    ordered = [quote(m, str(100 + m)) for m in range(0, 40)]
    shuffled = ordered[20:] + ordered[:20][::-1]
    bars = [consensus(m) for m in (3, 17, 25, 39, 45)]

    assert basis(bars, shuffled) == basis(bars, ordered)
    assert float(basis(bars, shuffled)[0]["venue_basis_bps"]) == pytest.approx(
        (103 / 100 - 1) * 10000
    )
