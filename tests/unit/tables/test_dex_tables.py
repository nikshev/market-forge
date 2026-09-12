"""The DeFi primitives as canonical tables (REQ-WP-053).

PRD §18.12 asks adapters to emit common economic primitives; §6.4 makes Iceberg
the canonical history. These tests write real Iceberg tables in a temporary
warehouse and read them back, because a schema that has never held a row is a
claim about types rather than a table.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.dex.depth import DepthCurve, DepthQuote
from channelflow.domain import ChainMeta, DexLiquidityEvent, DexSwapEvent, EventMeta
from channelflow.lakehouse import Catalog
from channelflow.tables import dex_depth, dex_liquidity, dex_swaps

#: Beyond int64, which is what `sqrt_price_x96` and `liquidity` routinely are.
HUGE = 2**100 + 7


def _meta(event_time_ns: int = 1_700_000_000_000_000_000) -> EventMeta:
    return EventMeta(
        source="evm-logs",
        venue="uniswap",
        market_type="spot",
        symbol="WETH/USDC",
        event_time_ns=event_time_ns,
        ingest_time_ns=event_time_ns + 1_000,
    )


def _chain(block_number: int = 21_000_000, log_index: int = 3) -> ChainMeta:
    return ChainMeta(
        chain_id=1,
        block_number=block_number,
        block_time_ns=1_700_000_000_000_000_000,
        tx_hash="0xabc",
        tx_index=1,
        log_index=log_index,
    )


def _swap(**overrides: object) -> DexSwapEvent:
    fields: dict[str, object] = {
        "meta": _meta(),
        "chain": _chain(),
        "dex": "uniswap_v3",
        "pool": "0xpool",
        "token0": "WETH",
        "token1": "USDC",
        # Signed: out of the pool is negative.
        "amount0": Decimal("-1.5"),
        "amount1": Decimal("4500.25"),
        "price_token1_per_token0": Decimal("3000.1666"),
        "notional_usd": Decimal("4500.25"),
        "sqrt_price_x96": HUGE,
        "tick": -201_000,
        "liquidity": HUGE + 1,
    }
    return DexSwapEvent(**{**fields, **overrides})  # type: ignore[arg-type]


def _liquidity(**overrides: object) -> DexLiquidityEvent:
    fields: dict[str, object] = {
        "meta": _meta(),
        "chain": _chain(log_index=4),
        "dex": "uniswap_v3",
        "pool": "0xpool",
        "event_type": "burn",
        "tick_lower": -202_000,
        "tick_upper": -200_000,
        # Signed and beyond int64: a burn of a large position.
        "liquidity_delta": -HUGE,
        "amount0": Decimal("0.5"),
        "amount1": Decimal("1500.75"),
    }
    return DexLiquidityEvent(**{**fields, **overrides})  # type: ignore[arg-type]


def _curve() -> DepthCurve:
    def quote(bps: str, *, reachable: bool) -> DepthQuote:
        return DepthQuote(
            reachable=reachable,
            target_bps=Decimal(bps),
            amount0=Decimal("1.25"),
            amount1=Decimal("3750.5"),
            reached_bps=Decimal(bps) if reachable else Decimal("17.5"),
            ticks_crossed=4,
            reason="" if reachable else "exhausted the known liquidity",
        )

    return DepthCurve(
        up={"10": quote("10", reachable=True), "100": quote("100", reachable=False)},
        down={"10": quote("10", reachable=True), "100": quote("100", reachable=True)},
        price=Decimal("3000.1666"),
    )


# --- swaps ---------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-053")
def test_a_swap_survives_the_round_trip(catalog: Catalog) -> None:
    table = dex_swaps.table_for(catalog)
    sink = dex_swaps.DexSwapSink(table=table)
    swap = _swap()
    sink(swap)
    assert sink.pending == 1
    assert sink.flush() is not None

    rows = table.read().to_pylist()
    assert len(rows) == 1
    restored = dex_swaps.from_row(rows[0])
    assert restored["pool"] == swap.pool
    assert restored["price_token1_per_token0"] == swap.price_token1_per_token0
    assert restored["tick"] == swap.tick


@pytest.mark.trace("REQ-WP-053")
def test_a_swap_keeps_the_sign_that_says_which_way_it_went(catalog: Catalog) -> None:
    """§18.12.1 asks for signed flow, and the sign *is* the direction: negative
    is out of the pool. Storing magnitudes and a side would be the same
    information in a shape that invites somebody to sum it."""
    table = dex_swaps.table_for(catalog)
    sink = dex_swaps.DexSwapSink(table=table)
    sink(_swap())
    sink.flush()

    restored = dex_swaps.from_row(table.read().to_pylist()[0])
    assert restored["amount0"] == Decimal("-1.5")
    assert restored["amount1"] == Decimal("4500.25")
    assert restored["amount0"] < 0 < restored["amount1"]  # type: ignore[operator]


@pytest.mark.trace("REQ-WP-053")
def test_a_price_beyond_int64_survives(catalog: Catalog) -> None:
    """`sqrt_price_x96` is uint160 and `liquidity` uint128 on chain. A column
    that overflowed silently would corrupt exactly the pools with the most
    liquidity."""
    assert HUGE > 2**63 - 1

    table = dex_swaps.table_for(catalog)
    sink = dex_swaps.DexSwapSink(table=table)
    sink(_swap())
    sink.flush()

    restored = dex_swaps.from_row(table.read().to_pylist()[0])
    assert restored["sqrt_price_x96"] == HUGE
    assert restored["liquidity"] == HUGE + 1


@pytest.mark.trace("REQ-WP-053")
def test_a_price_keeps_every_digit(catalog: Catalog) -> None:
    """A swap is money, and float64 cannot hold 0.1."""
    exact = Decimal("3000.1666666666666666666666666")
    table = dex_swaps.table_for(catalog)
    sink = dex_swaps.DexSwapSink(table=table)
    sink(_swap(price_token1_per_token0=exact))
    sink.flush()

    restored = dex_swaps.from_row(table.read().to_pylist()[0])
    assert restored["price_token1_per_token0"] == exact
    assert float(exact) != exact


@pytest.mark.trace("REQ-WP-053")
def test_an_absent_notional_stays_absent(catalog: Catalog) -> None:
    """A swap nobody priced in dollars is not a swap worth nothing."""
    table = dex_swaps.table_for(catalog)
    sink = dex_swaps.DexSwapSink(table=table)
    sink(_swap(notional_usd=None, sqrt_price_x96=None, liquidity=None, tick=None))
    sink.flush()

    restored = dex_swaps.from_row(table.read().to_pylist()[0])
    assert restored["notional_usd"] is None
    assert restored["sqrt_price_x96"] is None
    assert restored["liquidity"] is None
    assert restored["tick"] is None


@pytest.mark.trace("REQ-WP-053")
def test_the_columns_with_no_producer_are_absent_rather_than_null() -> None:
    """§18.12.1 lists `available_at`, `finality_status`, `fee_usd`,
    `price_before` and `price_after`. Nothing produces them today -- the first
    two are joined from [[REQ-WP-014]]'s chain records rather than carried by a
    swap -- and a column null on every row is a promise nothing keeps.
    """
    absent = {"available_at", "finality_status", "fee_usd", "price_before", "price_after"}
    assert absent.isdisjoint(dex_swaps.SCHEMA.names)


# --- liquidity ------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-053")
def test_a_burn_keeps_its_sign_and_its_magnitude(catalog: Catalog) -> None:
    """`liquidity_delta` is int128 and a burn is negative, so neither int64 nor
    an unsigned magnitude describes it: the first overflows on the largest
    positions and the second loses what distinguishes a mint from a burn."""
    table = dex_liquidity.table_for(catalog)
    sink = dex_liquidity.DexLiquiditySink(table=table)
    sink(_liquidity())
    sink.flush()

    restored = dex_liquidity.from_row(table.read().to_pylist()[0])
    assert restored["liquidity_delta"] == -HUGE
    assert restored["event_type"] == "burn"


@pytest.mark.trace("REQ-WP-053")
def test_a_collect_moves_no_liquidity_and_is_still_its_own_kind(catalog: Catalog) -> None:
    """Which is why the kind is stored rather than derived from the sign: a
    collect and a zero-delta modify would otherwise be the same row."""
    table = dex_liquidity.table_for(catalog)
    sink = dex_liquidity.DexLiquiditySink(table=table)
    sink(_liquidity(event_type="collect", liquidity_delta=0))
    sink(_liquidity(event_type="modify", liquidity_delta=0, chain=_chain(log_index=5)))
    sink.flush()

    kinds = [dex_liquidity.from_row(row)["event_type"] for row in table.read().to_pylist()]
    assert sorted(kinds) == ["collect", "modify"]


# --- depth ----------------------------------------------------------------------


@pytest.mark.trace("REQ-WP-053")
def test_a_curve_becomes_one_row_per_band_per_side(catalog: Catalog) -> None:
    """A schema with one column per band would need a migration the first time a
    liquidity regime wanted a different grid, which §18.12.3 says it will."""
    table = dex_depth.table_for(catalog)
    sink = dex_depth.DexDepthSink(table=table)
    sink(_curve(), chain_id=1, pool="0xpool", state_time_ns=1_700_000_000_000_000_000)
    assert sink.pending == 4
    sink.flush()

    rows = [dex_depth.from_row(row) for row in table.read().to_pylist()]
    assert len(rows) == 4
    assert {(row["side"], str(row["target_bps"])) for row in rows} == {
        ("up", "10"),
        ("up", "100"),
        ("down", "10"),
        ("down", "100"),
    }


@pytest.mark.trace("REQ-WP-053")
def test_an_unreachable_band_is_distinguishable_from_a_cheap_one(catalog: Catalog) -> None:
    """[[ADR-036]]'s distinction, which is the whole reason `reachable` is a
    column: both rows carry a notional and a band, and a pool too thin to move
    100 bps would otherwise read as a pool where 100 bps is cheap."""
    table = dex_depth.table_for(catalog)
    sink = dex_depth.DexDepthSink(table=table)
    sink(_curve(), chain_id=1, pool="0xpool", state_time_ns=1_700_000_000_000_000_000)
    sink.flush()

    rows = [dex_depth.from_row(row) for row in table.read().to_pylist()]
    unreachable = [row for row in rows if row["reachable"] is False]
    assert len(unreachable) == 1
    row = unreachable[0]
    assert row["side"] == "up"
    assert row["target_bps"] == Decimal("100")
    # It says how far the book actually went, which the target alone cannot.
    assert row["reached_bps"] == Decimal("17.5")
    assert row["reached_bps"] < row["target_bps"]  # type: ignore[operator]
    assert row["reason"]

    for reached in (row for row in rows if row["reachable"] is True):
        assert reached["reached_bps"] == reached["target_bps"]


@pytest.mark.trace("REQ-WP-053")
def test_both_sides_keep_their_own_tokens(catalog: Catalog) -> None:
    """Converting to one currency at write time would bake in the reference
    price and make the row unreadable at any other -- and comparing token0
    against token1 directly is the mistake that once reported every pool as
    asymmetric."""
    table = dex_depth.table_for(catalog)
    sink = dex_depth.DexDepthSink(table=table)
    sink(_curve(), chain_id=1, pool="0xpool", state_time_ns=1_700_000_000_000_000_000)
    sink.flush()

    rows = [dex_depth.from_row(row) for row in table.read().to_pylist()]
    for row in rows:
        assert row["amount0"] == Decimal("1.25")
        assert row["amount1"] == Decimal("3750.5")
        assert row["reference_price"] == Decimal("3000.1666")


# --- the properties every canonical table has -----------------------------------


@pytest.mark.trace("REQ-WP-053")
@pytest.mark.parametrize(
    "module", [dex_swaps, dex_liquidity, dex_depth], ids=["swaps", "liquidity", "depth"]
)
def test_a_flush_with_nothing_buffered_writes_no_snapshot(catalog: Catalog, module: object) -> None:
    """A snapshot identical to its parent under a new id would make every
    consumer keyed by snapshot see a change that did not happen."""
    table = module.table_for(catalog)  # type: ignore[attr-defined]
    sink_type = {
        dex_swaps: dex_swaps.DexSwapSink,
        dex_liquidity: dex_liquidity.DexLiquiditySink,
        dex_depth: dex_depth.DexDepthSink,
    }[module]  # type: ignore[index]
    assert sink_type(table=table).flush() is None


@pytest.mark.trace("REQ-WP-053")
@pytest.mark.parametrize(
    "module", [dex_swaps, dex_liquidity, dex_depth], ids=["swaps", "liquidity", "depth"]
)
def test_every_table_orders_by_columns_it_holds(module: object) -> None:
    """A read returns rows in this order, so two readers of one snapshot see the
    same series the same way."""
    names = set(module.SCHEMA.names)  # type: ignore[attr-defined]
    assert set(module.ORDER) <= names  # type: ignore[attr-defined]
    assert module.SCHEMA.event_time_column in names  # type: ignore[attr-defined]


@pytest.mark.trace("REQ-WP-053")
@pytest.mark.parametrize(
    "module", [dex_swaps, dex_liquidity, dex_depth], ids=["swaps", "liquidity", "depth"]
)
def test_every_table_has_its_own_name(module: object) -> None:
    names = {dex_swaps.TABLE_NAME, dex_liquidity.TABLE_NAME, dex_depth.TABLE_NAME}
    assert len(names) == 3
    assert module.TABLE_NAME in names  # type: ignore[attr-defined]


@pytest.mark.trace("REQ-WP-053")
def test_a_point_in_time_read_excludes_what_had_not_happened(catalog: Catalog) -> None:
    """Principle I, at the storage boundary: a read as of an instant must not
    return a swap that happened after it."""
    table = dex_swaps.table_for(catalog)
    sink = dex_swaps.DexSwapSink(table=table)
    early, late = 1_700_000_000_000_000_000, 1_700_000_100_000_000_000
    sink(_swap(meta=_meta(early)))
    sink(_swap(meta=_meta(late), chain=_chain(block_number=21_000_001)))
    sink.flush()

    assert len(table.read().to_pylist()) == 2
    as_of = table.read(as_of_ns=early).to_pylist()
    assert len(as_of) == 1
    assert dex_swaps.from_row(as_of[0])["event_time_ns"] == early
