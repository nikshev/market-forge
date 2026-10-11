"""The worker writes the cross-venue consensus every minute (REQ-WP-096, spec 148).

Every expected number is arithmetic done by hand. The rules pinned: the consensus at a close uses
only quotes at or before it; a refusal is stored with its reason and no price; the pass is
idempotent and resumes from its watermark; and what is stored is what the API's reads turn into the
venue-basis pane, which is checked against the formula, not against the pass's own arithmetic.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.api.repositories import select_consensus, select_venue_basis
from channelflow.crossvenue.deployment import (
    MARKETS,
    ConsensusMarket,
    build_registry,
    groups,
    representation_key,
)
from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.pipeline import consensus_pass as cp
from channelflow.tables import consensus as consensus_table
from channelflow.tables import quotes as quotes_table

SECOND = 1_000_000_000
MINUTE = 60 * SECOND
T0 = 1_791_699_960 * SECOND  # a whole minute

BYBIT = ConsensusMarket("BTC", "bybit", "BTCUSDT", "perp")
OKX = ConsensusMarket("BTC", "okx", "BTC-USDT-SWAP", "perp")
THIRD = ConsensusMarket("BTC", "binance", "BTCUSDT", "perp")  # a made-up third perpetual venue


def series_of(rows: list[tuple[int, str]]) -> cp.Series:
    return cp.Series.of([(t, Decimal(m)) for t, m in rows])


def per_minute(
    start_minute: int, end_minute: int, mid: str, *, lag: int = 1 * SECOND
) -> list[tuple[int, str]]:
    """A quote at the end of every minute from `start_minute` to `end_minute`, just before it."""
    return [(T0 + m * MINUTE - lag, mid) for m in range(start_minute, end_minute + 1)]


# --- the registry says who is comparable ---


@pytest.mark.trace("REQ-WP-096")
def test_bybit_and_okx_btc_are_one_asset_and_eth_is_another() -> None:
    registry = build_registry(MARKETS + (ConsensusMarket("ETH", "bybit", "ETHUSDT", "perp"),))

    assert registry.same_asset(representation_key(BYBIT), representation_key(OKX))
    eth = ConsensusMarket("ETH", "bybit", "ETHUSDT", "perp")
    assert not registry.same_asset(representation_key(BYBIT), representation_key(eth))


@pytest.mark.trace("REQ-WP-096")
def test_the_deployments_markets_group_by_asset_and_market_type_never_blended() -> None:
    by_group = groups()

    assert [m.venue for m in by_group[("BTC", "perp")]] == ["bybit", "okx"]
    assert [m.venue for m in by_group[("BTC", "spot")]] == ["binance", "okx"]
    assert ("ETH", "spot") in by_group and ("SOL", "spot") in by_group


# --- the consensus at one close ---


@pytest.mark.trace("REQ-WP-096")
def test_two_venues_give_the_interpolated_median() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100")]),
        ("okx", "BTC-USDT-SWAP"): series_of([(T0 - SECOND, "102")]),
    }

    closed = cp.consensus_at(
        (BYBIT, OKX), series, close_ns=T0, registry=build_registry((BYBIT, OKX))
    )

    assert (
        closed.consensus_mid == Decimal(101)
        and closed.venue_count == 2
        and closed.refusal_reason == ""
    )


@pytest.mark.trace("REQ-WP-096")
def test_three_venues_give_the_middle_one() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100")]),
        ("okx", "BTC-USDT-SWAP"): series_of([(T0 - SECOND, "110")]),
        ("binance", "BTCUSDT"): series_of([(T0 - SECOND, "103")]),
    }
    group = (BYBIT, OKX, THIRD)

    closed = cp.consensus_at(group, series, close_ns=T0, registry=build_registry(group))

    assert closed.consensus_mid == Decimal(103) and closed.venue_count == 3


@pytest.mark.trace("REQ-WP-096")
def test_one_venue_is_a_refusal_with_its_reason_and_no_price() -> None:
    series = {("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100")])}

    closed = cp.consensus_at(
        (BYBIT, OKX), series, close_ns=T0, registry=build_registry((BYBIT, OKX))
    )

    assert closed.consensus_mid is None and closed.venue_count == 1
    assert "only 1 venue" in closed.refusal_reason


@pytest.mark.trace("REQ-WP-096")
def test_a_stale_quote_does_not_contribute_and_the_count_says_so() -> None:
    old = T0 - cp.STALENESS_NS - 1
    series = {
        ("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100")]),
        ("okx", "BTC-USDT-SWAP"): series_of([(old, "102")]),
    }

    closed = cp.consensus_at(
        (BYBIT, OKX), series, close_ns=T0, registry=build_registry((BYBIT, OKX))
    )

    assert closed.consensus_mid is None and closed.venue_count == 1


@pytest.mark.trace("REQ-WP-096")
def test_the_staleness_bound_is_inclusive() -> None:
    edge = T0 - cp.STALENESS_NS
    series = {
        ("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100")]),
        ("okx", "BTC-USDT-SWAP"): series_of([(edge, "102")]),
    }
    closed = cp.consensus_at(
        (BYBIT, OKX), series, close_ns=T0, registry=build_registry((BYBIT, OKX))
    )
    assert closed.consensus_mid == Decimal(101)


@pytest.mark.trace("REQ-WP-096")
def test_a_quote_after_the_close_cannot_change_the_consensus_at_it() -> None:
    base = {
        ("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100")]),
        ("okx", "BTC-USDT-SWAP"): series_of([(T0 - SECOND, "102")]),
    }
    later = {
        ("bybit", "BTCUSDT"): series_of([(T0 - SECOND, "100"), (T0 + SECOND, "999")]),
        ("okx", "BTC-USDT-SWAP"): series_of([(T0 - SECOND, "102"), (T0 + 2 * SECOND, "1")]),
    }
    registry = build_registry((BYBIT, OKX))

    assert cp.consensus_at((BYBIT, OKX), base, close_ns=T0, registry=registry) == cp.consensus_at(
        (BYBIT, OKX), later, close_ns=T0, registry=registry
    )


# --- the rows -------------------------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-096")
def test_each_group_is_stored_under_every_symbol_its_members_use_so_either_chart_finds_it() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of(per_minute(1, 3, "100")),
        ("okx", "BTC-USDT-SWAP"): series_of(per_minute(1, 3, "102")),
    }

    rows = cp.compute_rows(series, {}, markets=(BYBIT, OKX))

    keyed = {(r["asset"], r["market_type"], r["bar_close_ns"]): r for r in rows}
    for close in (T0 + 2 * MINUTE, T0 + 3 * MINUTE):
        a = keyed[("BTCUSDT", "perp", close)]
        b = keyed[("BTC-USDT-SWAP", "perp", close)]
        assert a["consensus_mid"] == b["consensus_mid"] == Decimal(101)
        assert a["venue_count"] == b["venue_count"] == 2
    assert {r["asset"] for r in rows} == {"BTCUSDT", "BTC-USDT-SWAP"}


@pytest.mark.trace("REQ-WP-096")
def test_a_spot_group_of_one_venue_stores_a_refusal_every_minute() -> None:
    spot = ConsensusMarket("BTC", "binance", "BTCUSDT", "spot")
    series = {("binance", "BTCUSDT"): series_of(per_minute(1, 4, "100"))}

    rows = cp.compute_rows(series, {}, markets=(spot,))

    assert [r["bar_close_ns"] for r in rows] == [T0 + m * MINUTE for m in (1, 2, 3, 4)]
    assert all(
        r["consensus_mid"] is None and r["refusal_reason"] and r["venue_count"] == 1 for r in rows
    )
    assert all(r["market_type"] == "spot" for r in rows)


@pytest.mark.trace("REQ-WP-096")
def test_a_gap_in_the_quotes_is_a_run_of_refusal_rows_not_a_hole() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of(per_minute(1, 2, "100") + per_minute(8, 9, "100")),
        ("okx", "BTC-USDT-SWAP"): series_of(per_minute(1, 2, "102") + per_minute(8, 9, "102")),
    }

    rows = [r for r in cp.compute_rows(series, {}, markets=(BYBIT, OKX)) if r["asset"] == "BTCUSDT"]

    gap = [r for r in rows if T0 + 3 * MINUTE <= r["bar_close_ns"] <= T0 + 7 * MINUTE]
    assert len(gap) == 5
    assert all(r["consensus_mid"] is None and r["venue_count"] == 0 for r in gap)


@pytest.mark.trace("REQ-WP-096")
def test_the_pass_is_idempotent_and_resumes_from_its_watermark() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of(per_minute(1, 6, "100")),
        ("okx", "BTC-USDT-SWAP"): series_of(per_minute(1, 6, "102")),
    }
    first = cp.compute_rows(series, {}, markets=(BYBIT, OKX))
    watermark = {("BTCUSDT", "perp"): T0 + 4 * MINUTE, ("BTC-USDT-SWAP", "perp"): T0 + 4 * MINUTE}

    resumed = cp.compute_rows(series, watermark, markets=(BYBIT, OKX))
    full = {("BTCUSDT", "perp"): T0 + 6 * MINUTE, ("BTC-USDT-SWAP", "perp"): T0 + 6 * MINUTE}

    assert {r["bar_close_ns"] for r in resumed} == {T0 + 5 * MINUTE, T0 + 6 * MINUTE}
    assert len(resumed) == 4 and len(first) == 12  # six closes, two symbols each
    assert cp.compute_rows(series, full, markets=(BYBIT, OKX)) == []


@pytest.mark.trace("REQ-WP-096")
def test_each_symbol_resumes_from_its_own_watermark() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of(per_minute(1, 6, "100")),
        ("okx", "BTC-USDT-SWAP"): series_of(per_minute(1, 6, "102")),
    }
    watermark = {("BTCUSDT", "perp"): T0 + 4 * MINUTE, ("BTC-USDT-SWAP", "perp"): T0 + 2 * MINUTE}

    rows = cp.compute_rows(series, watermark, markets=(BYBIT, OKX))

    closes = {
        alias: sorted(r["bar_close_ns"] for r in rows if r["asset"] == alias)
        for alias in ("BTCUSDT", "BTC-USDT-SWAP")
    }
    assert closes["BTCUSDT"] == [T0 + 5 * MINUTE, T0 + 6 * MINUTE]
    assert closes["BTC-USDT-SWAP"] == [T0 + m * MINUTE for m in (3, 4, 5, 6)]


@pytest.mark.trace("REQ-WP-096")
def test_a_venue_that_lags_holds_the_pass_back_so_no_row_leaves_it_out() -> None:
    series = {
        ("bybit", "BTCUSDT"): series_of(per_minute(1, 8, "100")),
        ("okx", "BTC-USDT-SWAP"): series_of(per_minute(1, 4, "102")),  # four minutes behind
    }

    rows = cp.compute_rows(series, {}, markets=(BYBIT, OKX))

    assert max(r["bar_close_ns"] for r in rows) == T0 + 4 * MINUTE
    assert all(r["consensus_mid"] == Decimal(101) for r in rows)


@pytest.mark.trace("REQ-WP-096")
def test_a_venue_that_has_gone_quiet_for_good_stops_holding_the_pass_back() -> None:
    quiet_for = cp.DEAD_AFTER_NS // MINUTE + 5
    series = {
        ("bybit", "BTCUSDT"): series_of(per_minute(1, quiet_for + 25, "100")),
        ("okx", "BTC-USDT-SWAP"): series_of(per_minute(1, 3, "102")),
    }

    rows = cp.compute_rows(series, {}, markets=(BYBIT, OKX))

    assert max(r["bar_close_ns"] for r in rows) > T0 + 30 * MINUTE
    late = [r for r in rows if r["bar_close_ns"] > T0 + 30 * MINUTE]
    assert all(
        r["consensus_mid"] is None for r in late
    )  # the dead venue's quote is stale: a refusal


@pytest.mark.trace("REQ-WP-096")
def test_no_quotes_at_all_writes_nothing() -> None:
    assert cp.compute_rows({}, {}, markets=(BYBIT, OKX)) == []


# --- the pass against the tables and the API's reads ---


def store_quotes(catalog: Catalog, venue: str, symbol: str, rows: list[tuple[int, str]]) -> None:
    table = quotes_table.table_for(catalog)
    table.append(
        [
            quotes_table.to_row(
                quotes_table.Quote(
                    venue=venue,
                    symbol=symbol,
                    bid=Decimal(mid) - Decimal("0.5"),
                    ask=Decimal(mid) + Decimal("0.5"),
                    mid=Decimal(mid),
                    ts_ns=ts,
                    ingest_ns=-(-ts // MINUTE) * MINUTE,  # stored when its minute ended
                )
            )
            for ts, mid in rows
        ]
    )


@pytest.mark.trace("REQ-WP-096")
def test_the_pass_writes_the_table_and_a_second_pass_writes_nothing(catalog: Catalog) -> None:
    store_quotes(catalog, "bybit", "BTCUSDT", per_minute(1, 5, "100"))
    store_quotes(catalog, "okx", "BTC-USDT-SWAP", per_minute(1, 5, "102"))

    written = cp.write_consensus(catalog)

    assert written > 0
    assert cp.write_consensus(catalog) == 0
    rows = consensus_table.table_for(catalog).read().to_pylist()
    assert {r["asset"] for r in rows} >= {"BTCUSDT", "BTC-USDT-SWAP"}


@pytest.mark.trace("REQ-WP-096")
def test_what_is_stored_reads_back_as_the_venue_basis_formula_for_both_perpetual_venues(
    catalog: Catalog,
) -> None:
    store_quotes(catalog, "bybit", "BTCUSDT", per_minute(1, 6, "100.4"))
    store_quotes(catalog, "okx", "BTC-USDT-SWAP", per_minute(1, 6, "100.6"))
    cp.write_consensus(catalog)
    consensus_rows = consensus_table.table_for(catalog).read().to_pylist()
    quote_rows = quotes_table.table_for(catalog).read().to_pylist()

    for venue, symbol, mid in (
        ("bybit", "BTCUSDT", Decimal("100.4")),
        ("okx", "BTC-USDT-SWAP", Decimal("100.6")),
    ):
        points = select_venue_basis(
            consensus_rows,
            quote_rows,
            asset=symbol,
            market_type="perp",
            venue=venue,
            start_ns=T0,
            end_ns=T0 + 10 * MINUTE,
        )
        assert points, venue
        expected = float(10_000 * (mid / Decimal("100.5") - 1))
        assert all(p["venue_basis_bps"] == pytest.approx(expected) for p in points)


@pytest.mark.trace("REQ-WP-096")
def test_a_spot_series_reads_back_a_refusal_and_no_basis(catalog: Catalog) -> None:
    store_quotes(catalog, "binance", "BTCUSDT", per_minute(1, 4, "100"))
    cp.write_consensus(catalog)
    consensus_rows = consensus_table.table_for(catalog).read().to_pylist()
    quote_rows = quotes_table.table_for(catalog).read().to_pylist()

    bars = select_consensus(
        consensus_rows,
        asset="BTCUSDT",
        market_type="spot",
        window_ns=10 * MINUTE,
        at_ns=T0 + 5 * MINUTE,
    )
    basis = select_venue_basis(
        consensus_rows,
        quote_rows,
        asset="BTCUSDT",
        market_type="spot",
        venue="binance",
        start_ns=T0,
        end_ns=T0 + 10 * MINUTE,
    )

    assert bars and all(
        b["consensus_mid"] is None and "only 1 venue" in b["refusal_reason"] for b in bars
    )
    assert basis == []


@pytest.mark.trace("REQ-WP-096")
def test_a_failed_commit_is_reported_and_the_rows_come_back_next_pass(
    catalog: Catalog, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    store_quotes(catalog, "bybit", "BTCUSDT", per_minute(1, 4, "100"))
    store_quotes(catalog, "okx", "BTC-USDT-SWAP", per_minute(1, 4, "102"))
    original = IcebergTable.append

    def broken(self: IcebergTable, rows: object) -> object:
        if self.name == consensus_table.TABLE_NAME:
            raise OSError("object store down")
        return original(self, rows)  # type: ignore[arg-type]

    monkeypatch.setattr(IcebergTable, "append", broken)
    assert cp.write_consensus(catalog) == 0
    assert "could not write" in capsys.readouterr().out

    monkeypatch.setattr(IcebergTable, "append", original)
    assert cp.write_consensus(catalog) > 0


@pytest.mark.trace("REQ-WP-096")
def test_an_empty_quotes_table_is_a_pass_that_writes_nothing(catalog: Catalog) -> None:
    assert cp.write_consensus(catalog) == 0


@pytest.mark.trace("REQ-WP-098")
def test_every_spot_group_of_the_deployment_has_two_venues_and_an_alias_under_each_symbol() -> None:
    by_group = groups()
    for asset, okx_symbol, binance_symbol in (
        ("BTC", "BTC-USDT", "BTCUSDT"),
        ("ETH", "ETH-USDT", "ETHUSDT"),
        ("SOL", "SOL-USDT", "SOLUSDT"),
    ):
        group = by_group[(asset, "spot")]
        assert [m.venue for m in group] == ["binance", "okx"]
        assert {m.symbol for m in group} == {binance_symbol, okx_symbol}


@pytest.mark.trace("REQ-WP-098")
def test_two_spot_venues_give_a_consensus_stored_under_both_symbols() -> None:
    binance = ConsensusMarket("BTC", "binance", "BTCUSDT", "spot")
    okx = ConsensusMarket("BTC", "okx", "BTC-USDT", "spot")
    series = {
        ("binance", "BTCUSDT"): series_of(per_minute(1, 3, "100")),
        ("okx", "BTC-USDT"): series_of(per_minute(1, 3, "102")),
    }

    rows = cp.compute_rows(series, {}, markets=(binance, okx))

    assert {r["asset"] for r in rows} == {"BTCUSDT", "BTC-USDT"}
    assert all(r["consensus_mid"] == Decimal(101) and r["venue_count"] == 2 for r in rows)
    assert all(r["market_type"] == "spot" for r in rows)


@pytest.mark.trace("REQ-WP-099")
def test_the_hype_perpetual_group_has_two_venues_so_its_pane_has_a_consensus() -> None:
    group = groups()[("HYPE", "perp")]

    assert [(m.venue, m.symbol) for m in group] == [
        ("bybit", "HYPEUSDT"),
        ("okx", "HYPE-USDT-SWAP"),
    ]
