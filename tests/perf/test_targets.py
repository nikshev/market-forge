"""PRD §36's targets, measured against the real paths (REQ-WP-057).

These run in the ordinary suite and need no service beyond a temporary
warehouse. They are not a load test in the usual sense -- nothing here generates
concurrent traffic against a deployed system, because nothing is deployed
([[REQ-WP-056]] records that gap). What they do is measure the paths a user waits
on and guard the property that would degrade them.

**Two kinds of assertion, and only one of them would catch a regression early.**
The target is the promise made to a user and is asserted because breaking it
matters; with fiftyfold headroom it would keep passing through a fortyfold
regression. The scaling ratio is what bites: a change making a linear read
quadratic fails it on a fast machine and a slow one alike, because a ratio
between two measurements from the same run divides the machine out.
"""

from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from channelflow.api.lakehouse_repository import LakehouseRepository
from channelflow.bars import Bar
from channelflow.channels.huber import HuberChannel
from channelflow.channels.kalman import KalmanChannel
from channelflow.channels.quantile import QuantileChannel
from channelflow.channels.rolling_ols import RollingOLSChannel
from channelflow.domain import EventMeta, TradeEvent
from channelflow.features.flow import FlowTracker
from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.perf import TARGETS, headroom, scaling_ratio, timed
from channelflow.tables import bars as bars_table

BASE_NS = 1_700_000_000_000_000_000
MINUTE_NS = 60 * 1_000_000_000

#: §36's own figure. The target is stated for this size and measuring another
#: would be answering a different question.
CHART_BARS = 2_000

#: How many times each operation runs. Enough for a p95 to mean something --
#: twenty samples put the p95 on the nineteenth, so one slow run shows.
REPEATS = 20

#: What a doubling may cost. Linear gives about 2, quadratic about 4, and the
#: bound sits between them with room for the fixed overhead that makes small
#: sizes cheaper per row.
MAX_DOUBLING_RATIO = 3.0


def _target(name: str) -> object:
    return next(target for target in TARGETS if target.name == name)


def _bar(index: int) -> Bar:
    price = Decimal(100 + (index % 7))
    return Bar(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        open_time_ns=BASE_NS + index * MINUTE_NS,
        close_time_ns=BASE_NS + (index + 1) * MINUTE_NS,
        open=price,
        high=price + 1,
        low=price - 1,
        close=price + Decimal("0.5"),
        volume_base=Decimal(1),
        volume_quote=price,
        trade_count=10,
        aggressive_buy_base=Decimal("0.5"),
        aggressive_sell_base=Decimal("0.5"),
        delta_base=Decimal(0),
        vwap=price,
        high_time_ns=BASE_NS + index * MINUTE_NS,
        low_time_ns=BASE_NS + index * MINUTE_NS,
        first_trade_id="a",
        last_trade_id="b",
        is_final=True,
    )


def _seeded(rows: int) -> LakehouseRepository:
    """A warehouse holding `rows` bars, through the real write path."""
    warehouse = Path(tempfile.mkdtemp())
    catalog: Catalog = open_catalog(
        uri=f"sqlite:///{warehouse}/catalog.db", warehouse=str(warehouse)
    )
    sink = bars_table.BarSink(table=bars_table.table_for(catalog))
    for index in range(rows):
        sink(_bar(index))
    sink.flush()
    return LakehouseRepository(catalog=catalog)


def _read(repository: LakehouseRepository, limit: int) -> object:
    return repository.bars(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        start_ns=None,
        end_ns=None,
        limit=limit,
    )


# --- the promises §36 makes ------------------------------------------------------


@pytest.mark.trace("REQ-WP-057")
def test_a_chart_loads_two_thousand_bars_inside_its_budget() -> None:
    """§36: "chart historical load p95 < 2s for 2,000 bars"."""
    repository = _seeded(CHART_BARS)
    _read(repository, CHART_BARS)  # warm: the first read is not the question here

    measurement = timed(
        lambda: _read(repository, CHART_BARS), name="chart_historical_load", repeats=REPEATS
    )
    target = _target("chart_historical_load")
    assert measurement.p95_ns < target.budget_ns  # type: ignore[attr-defined]

    # Reported, not only compared. A target met with fifty times to spare and
    # one met with one and a half are the same pass, and the difference is the
    # only warning anybody gets.
    print(
        f"\n{target.stated}: p50={measurement.p50_ns / 1e6:.1f}ms "  # type: ignore[attr-defined]
        f"p95={measurement.p95_ns / 1e6:.1f}ms "
        f"headroom={headroom(measurement, target):.0f}x "  # type: ignore[arg-type]
        f"spread={measurement.spread:.2f}x"
    )


@pytest.mark.trace("REQ-WP-057")
@pytest.mark.parametrize(
    "model",
    [RollingOLSChannel, QuantileChannel, HuberChannel, KalmanChannel],
    ids=lambda cls: cls.__name__,
)
def test_a_channel_fits_inside_the_signal_budget(model: type) -> None:
    """§36: "signal after bar close <= 2s". The fit is the heaviest part of that
    path, and all four models are measured because the slowest is the one the
    budget has to cover."""
    window = [_bar(index) for index in range(60)]
    channel = model()
    as_of_ns = BASE_NS + 61 * MINUTE_NS
    channel.fit(window, as_of_ns=as_of_ns)

    measurement = timed(
        lambda: channel.fit(window, as_of_ns=as_of_ns),
        name=f"fit:{model.__name__}",
        repeats=REPEATS,
    )
    target = _target("signal_after_bar_close")
    assert measurement.p95_ns < target.budget_ns  # type: ignore[attr-defined]
    print(
        f"\n{model.__name__}: p95={measurement.p95_ns / 1e6:.2f}ms "
        f"headroom={headroom(measurement, target):.0f}x"  # type: ignore[arg-type]
    )


@pytest.mark.trace("REQ-WP-057")
def test_a_feature_updates_inside_its_budget() -> None:
    """§36: "feature update <= 1s"."""
    tracker = FlowTracker()

    def trade(index: int) -> TradeEvent:
        return TradeEvent(
            meta=EventMeta(
                source="binance-ws",
                venue="binance",
                market_type="spot",
                symbol="BTCUSDT",
                event_time_ns=BASE_NS + index,
                ingest_time_ns=BASE_NS + index,
            ),
            trade_id=str(index),
            price=Decimal("100"),
            qty_base=Decimal("1"),
            notional_quote=Decimal("100"),
            aggressor_side="buy",
            is_buyer_maker=False,
        )

    counter = iter(range(1, REPEATS + 2))
    tracker.observe(trade(0))

    measurement = timed(
        lambda: tracker.observe(trade(next(counter))), name="feature_update", repeats=REPEATS
    )
    target = _target("feature_update")
    assert measurement.p95_ns < target.budget_ns  # type: ignore[attr-defined]
    print(
        f"\nfeature update: p95={measurement.p95_ns / 1e3:.1f}us "
        f"headroom={headroom(measurement, target):.0f}x"  # type: ignore[arg-type]
    )


# --- the assertion that would actually catch a regression -------------------------


@pytest.mark.trace("REQ-WP-057")
def test_the_read_stays_linear_as_the_series_grows() -> None:
    """The guard that bites.

    A change making this quadratic passes the two-second threshold at two
    thousand bars and falls over at twenty thousand. A ratio between two
    measurements from the same run divides the machine out, so this fails on a
    fast runner and a slow one alike -- which a duration cannot.
    """
    sizes = (1_000, 2_000, 4_000)
    measurements = []
    for rows in sizes:
        repository = _seeded(rows)
        _read(repository, rows)
        measurements.append(
            timed(lambda r=repository, n=rows: _read(r, n), name=f"read:{rows}", repeats=7)
        )

    ratios = scaling_ratio(measurements)
    print(f"\nread scaling across {sizes}: {[f'{r:.2f}x' for r in ratios]}")
    for ratio in ratios:
        assert ratio < MAX_DOUBLING_RATIO, ratios


@pytest.mark.trace("REQ-WP-057")
def test_the_scaling_guard_fails_on_something_quadratic() -> None:
    """The guard is only worth having if it is known to bite.

    A deliberately quadratic operation, measured the same way: the ratios land
    near four rather than near two, and the bound refuses them.
    """

    def quadratic(rows: int) -> None:
        total = 0
        for outer in range(rows):
            for inner in range(rows):
                total += outer ^ inner

    sizes = (200, 400, 800)
    measurements = [
        timed(lambda n=rows: quadratic(n), name=f"quadratic:{rows}", repeats=3) for rows in sizes
    ]
    ratios = scaling_ratio(measurements)
    print(f"\nquadratic scaling across {sizes}: {[f'{r:.2f}x' for r in ratios]}")
    assert any(ratio >= MAX_DOUBLING_RATIO for ratio in ratios), ratios


@pytest.mark.trace("REQ-WP-057")
def test_a_linear_operation_passes_the_same_guard() -> None:
    """The other direction, so the guard is not simply strict.

    Without this, a bound low enough to fail everything would pass the test
    above and look like a working guard.
    """

    def linear(rows: int) -> None:
        total = 0
        for index in range(rows * 2_000):
            total += index

    sizes = (200, 400, 800)
    measurements = [
        timed(lambda n=rows: linear(n), name=f"linear:{rows}", repeats=3) for rows in sizes
    ]
    ratios = scaling_ratio(measurements)
    print(f"\nlinear scaling across {sizes}: {[f'{r:.2f}x' for r in ratios]}")
    for ratio in ratios:
        assert ratio < MAX_DOUBLING_RATIO, ratios
