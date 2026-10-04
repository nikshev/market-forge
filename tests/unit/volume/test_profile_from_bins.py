"""The profile from stored price bins equals the profile from the trades (REQ-WP-089, PRD section
14.1).

`profile.build` bins trades and finds the POC and the value area (ADR-028); `from_bins` must reach
the same numbers from the bins the ingest stored, because the two are one definition. They are
compared by bin edges and volumes, not by index: `build` renumbers its bins by position.
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from channelflow.tables.volume_bins import StoredBin
from channelflow.volume.bins import BinBlock, PriceBinBuilder
from channelflow.volume.profile import EmptyProfile, build, from_bins

from ..features.conftest import BASE_NS, trade

BLOCK_NS = 300_000_000_000
SECOND_NS = 1_000_000_000
START = (BASE_NS // BLOCK_NS) * BLOCK_NS
WIDTH = Decimal("10")


def trades(count: int = 400, seed: int = 11):
    rng = random.Random(seed)
    out = []
    for i in range(count):
        # three blocks of trades, prices clustered around two levels so the value area is not the
        # whole profile
        centre = Decimal(1000) if rng.random() < 0.6 else Decimal(1090)
        price = centre + Decimal(rng.randint(-60, 60)) + Decimal(rng.randint(0, 99)) / 100
        side = rng.choice(["buy", "sell", "sell", "buy", "unknown"])
        at = START + (i * 3 * BLOCK_NS // count) + SECOND_NS
        out.append(trade(str(i), str(price), str(Decimal(rng.randint(1, 50)) / 10), side, at_ns=at))
    return out


def blocks_of(all_trades) -> list[BinBlock]:
    blocks: list[BinBlock] = []
    made = PriceBinBuilder(block_ns=BLOCK_NS, bin_width=WIDTH, on_final=blocks.append)
    for t in sorted(all_trades, key=lambda t: t.meta.event_time_ns):
        made.add(t)
    made.add(trade("end", "1000", "1", "buy", at_ns=START + 4 * BLOCK_NS + 6 * SECOND_NS))
    return blocks


def stored(blocks: list[BinBlock]) -> list[StoredBin]:
    return [
        StoredBin(
            b.block_open_time_ns,
            b.block_ns,
            b.bin_width,
            r.index,
            r.buy,
            r.sell,
            r.unknown,
            r.trades,
        )
        for b in blocks
        for r in b.bins
    ]


@pytest.mark.trace("REQ-WP-089")
def test_the_profile_from_stored_bins_equals_the_profile_from_the_trades() -> None:
    """SC-002: the same trades on the same grid (anchored at zero) give the same bins, POC and value
    area."""
    all_trades = trades()
    blocks = blocks_of(all_trades)
    counted = {
        t.trade_id for t in all_trades if START <= t.meta.event_time_ns < START + 3 * BLOCK_NS
    }
    in_blocks = [t for t in all_trades if t.trade_id in counted]

    expected = build(in_blocks, bin_width=WIDTH, anchor=Decimal(0))
    got = from_bins(stored(blocks), bin_width=WIDTH)

    assert [(b.low, b.high, b.volume, b.buy_volume, b.sell_volume) for b in got.bins] == [
        (b.low, b.high, b.volume, b.buy_volume, b.sell_volume) for b in expected.bins
    ]
    assert (got.poc.low, got.poc.high) == (expected.poc.low, expected.poc.high)
    assert (got.val, got.vah) == (expected.val, expected.vah)
    assert got.value_area_is_whole_profile == expected.value_area_is_whole_profile
    assert got.poc_tie == expected.poc_tie
    assert got.total_volume == expected.total_volume


@pytest.mark.trace("REQ-WP-089")
def test_blocks_are_summed_per_bin_across_time() -> None:
    first = stored(blocks_of([trade("1", "105", "2", "buy", at_ns=START + SECOND_NS)]))
    second = [
        StoredBin(
            START + BLOCK_NS, BLOCK_NS, WIDTH, 10, Decimal("3"), Decimal("1"), Decimal("0"), 2
        )
    ]

    profile = from_bins(first + second, bin_width=WIDTH)

    assert len(profile.bins) == 1
    only = profile.bins[0]
    assert (only.buy_volume, only.sell_volume, only.volume, only.trades) == (5, 1, 6, 3)


@pytest.mark.trace("REQ-WP-089")
def test_unknown_volume_counts_to_the_bin_and_to_neither_side() -> None:
    rows = [StoredBin(START, BLOCK_NS, WIDTH, 10, Decimal("1"), Decimal("2"), Decimal("4"), 3)]

    only = from_bins(rows, bin_width=WIDTH).bins[0]

    assert (only.buy_volume, only.sell_volume, only.volume) == (1, 2, 7)


@pytest.mark.trace("REQ-WP-089")
def test_one_bin_is_a_valid_profile_and_says_the_value_area_is_the_whole_of_it() -> None:
    rows = [StoredBin(START, BLOCK_NS, WIDTH, 10, Decimal("1"), Decimal("1"), Decimal("0"), 2)]

    profile = from_bins(rows, bin_width=WIDTH)

    assert profile.poc.low == Decimal("100")
    assert profile.value_area_indices == (0,)


@pytest.mark.trace("REQ-WP-089")
def test_no_bins_is_refused_rather_than_an_empty_profile() -> None:
    with pytest.raises(EmptyProfile):
        from_bins([], bin_width=WIDTH)
