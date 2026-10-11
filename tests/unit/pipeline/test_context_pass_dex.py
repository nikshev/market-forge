"""The worker pass writes the two DEX features for the series the pools price (REQ-WP-099)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dex import hyperevm_pools as registry
from channelflow.domain import ChainMeta, DexSwapEvent, EventMeta
from channelflow.lakehouse import Catalog
from channelflow.pipeline import context_pass as write
from channelflow.tables import dex_state, dex_swaps
from tests.unit.pipeline.test_context_pass import MINUTE, features_for, make_bar

pytestmark = pytest.mark.trace("REQ-WP-099")

VENUE, SYMBOL = registry.SERIES[0]
A, B = (pool.address for pool in registry.POOLS)
SECOND = 1_000_000_000


def bar(index: int, **kw: object):
    return make_bar(index, venue=VENUE, symbol=SYMBOL, **kw)  # type: ignore[arg-type]


def swap(
    at: int,
    amount0: str,
    *,
    ingest: int | None = None,
    pool: str = A,
    n: int = 0,
    chain_id: int = 999,
) -> DexSwapEvent:
    return DexSwapEvent(
        meta=EventMeta(
            source="hyperevm-rpc",
            venue="hyperevm",
            market_type="dex",
            symbol=pool,
            event_time_ns=at,
            ingest_time_ns=at + SECOND if ingest is None else ingest,
        ),
        chain=ChainMeta(
            chain_id=chain_id,
            block_number=at // SECOND,
            block_time_ns=at,
            tx_hash="0xt",
            tx_index=0,
            log_index=n,
        ),
        dex="uniswap_v3",
        pool=pool,
        token0=registry.WHYPE,
        token1=registry.USDC,
        amount0=Decimal(amount0),
        amount1=Decimal("-1"),
        price_token1_per_token0=Decimal(40),
    )


def reading(at: int, pool: str, liquidity: int = 1_000) -> dict[str, object]:
    return dex_state.reading_row(
        chain_id=999,
        venue="hyperevm",
        protocol="uniswap_v3",
        pool=pool,
        state_time_ns=at,
        reference_price=Decimal(40),
        active_liquidity=liquidity,
        fee_state=500,
        block=at // SECOND,
    )


def store(
    catalog: Catalog,
    swaps: list[DexSwapEvent],
    *,
    through: int,
    minutes: int = 120,
    pools: tuple[str, ...] = (A, B),
) -> None:
    swap_sink = dex_swaps.DexSwapSink(dex_swaps.table_for(catalog))
    swap_sink.extend(swaps)
    swap_sink.flush()
    state_sink = dex_state.DexStateSink(dex_state.table_for(catalog))
    for half_minute in range(minutes * 2):
        for pool in pools:
            state_sink(reading(through - half_minute * 30 * SECOND, pool, 1_000 + half_minute))
    state_sink.flush()


def test_the_pass_writes_both_features_at_a_covered_close(catalog: Catalog) -> None:
    b = bar(30)
    close = b.close_time_ns
    store(
        catalog,
        [swap(close - 3 * MINUTE, "3"), swap(close - MINUTE, "-1", pool=B, n=1)],
        through=close + 10 * MINUTE,
    )

    written = write.write_context_features(catalog, [b])

    got = features_for(catalog, VENUE, SYMBOL, MINUTE)[close]
    assert got["dex_swap_imbalance"] == pytest.approx(0.5)
    assert got["dex_active_liquidity"] > 0
    assert written >= 2


def test_the_value_at_a_close_does_not_change_when_later_swaps_arrive(catalog: Catalog) -> None:
    b = bar(30)
    close = b.close_time_ns
    store(catalog, [swap(close - 2 * MINUTE, "1")], through=close + 10 * MINUTE)
    write.write_context_features(catalog, [b])
    first = features_for(catalog, VENUE, SYMBOL, MINUTE)[close]["dex_swap_imbalance"]

    later = dex_swaps.DexSwapSink(dex_swaps.table_for(catalog))
    later(swap(close + 30 * SECOND, "-50", n=2))
    later.flush()
    write.write_context_features(catalog, [b, bar(31)])

    assert features_for(catalog, VENUE, SYMBOL, MINUTE)[close]["dex_swap_imbalance"] == first


def test_a_swap_stored_after_the_close_is_not_in_the_bar(catalog: Catalog) -> None:
    b = bar(30)
    close = b.close_time_ns
    store(
        catalog,
        [swap(close - 2 * MINUTE, "1"), swap(close - SECOND, "-9", ingest=close + MINUTE, n=1)],
        through=close + 10 * MINUTE,
    )

    write.write_context_features(catalog, [b])

    assert features_for(catalog, VENUE, SYMBOL, MINUTE)[close]["dex_swap_imbalance"] == 1.0


def test_a_bar_the_collector_did_not_cover_gets_no_imbalance(catalog: Catalog) -> None:
    b = bar(30)
    close = b.close_time_ns
    store(catalog, [swap(close - MINUTE, "1")], through=close - 20 * MINUTE)

    write.write_context_features(catalog, [b])

    assert features_for(catalog, VENUE, SYMBOL, MINUTE).get(close, {}) == {}


def test_a_covered_bar_with_no_swap_has_liquidity_and_no_imbalance(catalog: Catalog) -> None:
    b = bar(30)
    store(catalog, [], through=b.close_time_ns + 10 * MINUTE)

    write.write_context_features(catalog, [b])

    got = features_for(catalog, VENUE, SYMBOL, MINUTE)[b.close_time_ns]
    assert "dex_swap_imbalance" not in got
    assert "dex_active_liquidity" in got


def test_a_second_pass_writes_nothing_more(catalog: Catalog) -> None:
    b = bar(30)
    store(catalog, [swap(b.close_time_ns - MINUTE, "1")], through=b.close_time_ns + 10 * MINUTE)
    write.write_context_features(catalog, [b])

    assert write.write_context_features(catalog, [b]) == 0


def test_a_series_without_pools_gets_no_dex_feature(catalog: Catalog) -> None:
    other = make_bar(30, venue="bybit", symbol="BTCUSDT")
    store(
        catalog,
        [swap(other.close_time_ns - MINUTE, "1")],
        through=other.close_time_ns + 10 * MINUTE,
    )

    write.write_context_features(catalog, [other])

    assert features_for(catalog, "bybit", "BTCUSDT", MINUTE).get(other.close_time_ns, {}) == {}


def test_a_pass_with_no_dex_tables_content_writes_nothing_for_them(catalog: Catalog) -> None:
    assert write.write_context_features(catalog, [bar(30)]) == 0


def test_a_swap_of_another_chain_is_not_one_of_the_pools(catalog: Catalog) -> None:
    b = bar(30)
    close = b.close_time_ns
    store(
        catalog,
        [swap(close - 2 * MINUTE, "1"), swap(close - MINUTE, "-9", n=1, chain_id=1)],
        through=close + 10 * MINUTE,
    )

    write.write_context_features(catalog, [b])

    assert features_for(catalog, VENUE, SYMBOL, MINUTE)[close]["dex_swap_imbalance"] == 1.0


def test_every_market_the_pools_price_gets_the_features(catalog: Catalog) -> None:
    close = bar(30).close_time_ns
    store(catalog, [swap(close - 2 * MINUTE, "1")], through=close + 10 * MINUTE)
    bars = [make_bar(30, venue=v, symbol=s) for v, s in registry.SERIES]

    write.write_context_features(catalog, bars)

    for venue, symbol in registry.SERIES:
        got = features_for(catalog, venue, symbol, MINUTE)[close]
        assert got["dex_swap_imbalance"] == 1.0, (venue, symbol)
