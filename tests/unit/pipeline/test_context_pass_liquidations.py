"""The worker pass writes the liquidation features beside the derivatives ones (REQ-WP-094)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import EventMeta, LiquidationEvent
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.pipeline import context_pass as write
from channelflow.tables import features as features_table
from channelflow.tables import liquidations as liq_table
from tests.unit.pipeline.test_context_pass import (
    HOUR,
    MINUTE,
    T0,
    binance_states,
    features_for,
    make_bar,
    store,
)

LIQUIDATION_FEATURES = (
    "liquidation_long_usd_5m",
    "liquidation_short_usd_5m",
    "liquidation_imbalance_5m",
)
START = T0 + 1 * HOUR


def liquidation(
    at: int, side: str, usd: str, *, ingest: int | None = None, symbol: str = "BTCUSDT"
) -> LiquidationEvent:
    return LiquidationEvent(
        meta=EventMeta(
            source="binance-ws-liquidation",
            venue="binance",
            market_type="perp",
            symbol=symbol,
            event_time_ns=at,
            ingest_time_ns=at if ingest is None else ingest,
            sequence=None,
            source_event_id=None,
        ),
        side=side,  # type: ignore[arg-type]
        price=Decimal(1),
        qty=Decimal(usd),
        notional_usd=Decimal(usd),
    )


def store_liquidations(
    catalog: Catalog,
    events: list[LiquidationEvent],
    *,
    heartbeats: range | None = range(0, 120),
    symbol: str = "BTCUSDT",
) -> None:
    sink = liq_table.LiquidationSink(liq_table.table_for(catalog))
    for item in events:
        sink(item)
    for minute in heartbeats or []:
        sink.heartbeat(
            liq_table.Heartbeat(venue="binance", symbol=symbol, at_ns=START + minute * MINUTE)
        )
    sink.flush()


@pytest.mark.trace("REQ-WP-094")
def test_the_pass_writes_the_three_liquidation_features_for_covered_bars(catalog: Catalog) -> None:
    close = make_bar(30).close_time_ns
    store_liquidations(
        catalog,
        [
            liquidation(close - 2 * MINUTE, "long_liquidated", "300"),
            liquidation(close - 1 * MINUTE, "short_liquidated", "100"),
        ],
    )

    written = write.write_context_features(catalog, [make_bar(30)])

    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)[close]
    assert got["liquidation_long_usd_5m"] == 300.0
    assert got["liquidation_short_usd_5m"] == 100.0
    assert got["liquidation_imbalance_5m"] == pytest.approx(0.5)
    assert written == len(LIQUIDATION_FEATURES)


@pytest.mark.trace("REQ-WP-094")
def test_a_bar_the_stream_did_not_cover_gets_no_liquidation_feature(catalog: Catalog) -> None:
    store_liquidations(
        catalog,
        [liquidation(START + 28 * MINUTE, "long_liquidated", "300")],
        heartbeats=range(0, 20),
    )

    assert write.write_context_features(catalog, [make_bar(30)]) == 0


@pytest.mark.trace("REQ-WP-094")
def test_a_quiet_covered_bar_has_zero_sums_and_no_imbalance_row(catalog: Catalog) -> None:
    store_liquidations(catalog, [])

    write.write_context_features(catalog, [make_bar(30)])

    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)[make_bar(30).close_time_ns]
    assert got == {"liquidation_long_usd_5m": 0.0, "liquidation_short_usd_5m": 0.0}


@pytest.mark.trace("REQ-WP-094")
def test_an_event_delivered_after_the_close_is_not_in_the_bar(catalog: Catalog) -> None:
    close = make_bar(30).close_time_ns
    store_liquidations(
        catalog,
        [liquidation(close - MINUTE, "long_liquidated", "900", ingest=close + 5 * MINUTE)],
    )

    write.write_context_features(catalog, [make_bar(30)])

    assert (
        features_for(catalog, "binance", "BTCUSDT", MINUTE)[close]["liquidation_long_usd_5m"] == 0.0
    )


@pytest.mark.trace("REQ-WP-094")
def test_a_second_pass_writes_nothing_more(catalog: Catalog) -> None:
    store_liquidations(catalog, [])
    bars = [make_bar(i) for i in range(30, 36)]
    write.write_context_features(catalog, bars)

    assert write.write_context_features(catalog, bars) == 0


@pytest.mark.trace("REQ-WP-094")
def test_derivatives_and_liquidations_are_one_commit(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    store(catalog, binance_states())
    store_liquidations(catalog, [])
    commits: list[int] = []
    original = IcebergTable.append

    def counting(self: IcebergTable, rows: object) -> object:
        if self.name == features_table.features_table_for(catalog).name:
            commits.append(len(rows))  # type: ignore[arg-type]
        return original(self, rows)  # type: ignore[arg-type]

    monkeypatch.setattr(IcebergTable, "append", counting)

    written = write.write_context_features(catalog, [make_bar(i) for i in range(30, 36)])

    assert commits == [written]
    got = features_for(catalog, "binance", "BTCUSDT", MINUTE)[make_bar(30).close_time_ns]
    assert {"open_interest_usd", "liquidation_long_usd_5m"} <= set(got)


@pytest.mark.trace("REQ-WP-094")
def test_a_series_with_no_perpetual_gets_no_liquidation_features(catalog: Catalog) -> None:
    store_liquidations(catalog, [], symbol="DOGEUSDT")
    assert write.write_context_features(catalog, [make_bar(30, symbol="DOGEUSDT")]) == 0


@pytest.mark.trace("REQ-WP-094")
def test_one_series_failing_in_the_liquidation_step_is_reported_and_the_others_go_on(
    catalog: Catalog, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from channelflow.features import liquidation_values

    store_liquidations(catalog, [])
    store_liquidations(catalog, [], symbol="ETHUSDT")
    original = liquidation_values.liquidation_values

    def explode(
        events: list[LiquidationEvent], heartbeats: list[int], **kwargs: object
    ) -> dict[str, float]:
        if kwargs.get("symbol") == "ETHUSDT":
            raise RuntimeError("boom")
        return original(events, heartbeats, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(write, "liquidation_values", explode)

    write.write_context_features(catalog, [make_bar(30, symbol="ETHUSDT"), make_bar(30)])

    assert features_for(catalog, "binance", "BTCUSDT", MINUTE)
    assert "ETHUSDT" in capsys.readouterr().out
