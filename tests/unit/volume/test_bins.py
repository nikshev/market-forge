"""Price bins collected from the trades (REQ-WP-089, PRD section 14.1).

Every expected value is arithmetic done by hand. The ingest aggregates per five-minute block and
per price bin, from the aggressor side only; a block is written once, when it closes, and a block
whose trade ids show missed trades is dropped.
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from channelflow.volume.bins import BinBlock, PriceBinBuilder, nice_bin_width, parse_bin_widths

from ..features.conftest import BASE_NS, trade

BLOCK_NS = 300_000_000_000
SECOND_NS = 1_000_000_000
START = (BASE_NS // BLOCK_NS) * BLOCK_NS


def builder(*, width: str | None = "10", sequential_ids: bool = False):
    blocks: list[BinBlock] = []
    made = PriceBinBuilder(
        block_ns=BLOCK_NS,
        bin_width=Decimal(width) if width is not None else None,
        sequential_ids=sequential_ids,
        on_final=blocks.append,
    )
    return made, blocks


def close(made: PriceBinBuilder, *, after_block: int = 0) -> None:
    """A trade late enough in a later block to close the one under test."""
    made.add(
        trade("z", "100", "1", "buy", at_ns=START + (after_block + 1) * BLOCK_NS + 6 * SECOND_NS)
    )


def by_index(block: BinBlock):
    return {b.index: b for b in block.bins}


@pytest.mark.trace("REQ-WP-089")
def test_each_bin_holds_the_buy_sell_and_unknown_volume_of_its_trades_by_aggressor_side() -> None:
    """SC-001. Bin 10 is [100, 110), bin 11 is [110, 120)."""
    made, blocks = builder()
    for i, (price, qty, side) in enumerate(
        [
            ("100.0", "2", "buy"),
            ("105.5", "3", "buy"),
            ("109.9", "1", "sell"),
            ("110.0", "4", "buy"),
            ("115.0", "5", "sell"),
            ("119.9", "6", "unknown"),
        ]
    ):
        made.add(trade(str(i), price, qty, side, at_ns=START + (i + 1) * SECOND_NS))
    close(made)

    bins = by_index(blocks[0])

    assert (bins[10].buy, bins[10].sell, bins[10].unknown, bins[10].trades) == (5, 1, 0, 3)
    assert (bins[11].buy, bins[11].sell, bins[11].unknown, bins[11].trades) == (4, 5, 6, 3)
    assert set(bins) == {10, 11}


@pytest.mark.trace("REQ-WP-089")
def test_a_price_exactly_on_a_bin_edge_falls_in_the_upper_bin() -> None:
    made, blocks = builder()
    made.add(trade("a", "110", "1", "buy", at_ns=START + SECOND_NS))
    close(made)

    assert set(by_index(blocks[0])) == {11}


@pytest.mark.trace("REQ-WP-089")
def test_a_trade_on_a_block_boundary_belongs_to_the_block_that_opens_there() -> None:
    made, blocks = builder()
    made.add(trade("a", "100", "1", "buy", at_ns=START + SECOND_NS))
    made.add(trade("b", "100", "7", "buy", at_ns=START + BLOCK_NS))
    close(made, after_block=1)

    assert len(blocks) == 2
    assert blocks[0].block_open_time_ns == START
    assert by_index(blocks[0])[10].buy == 1
    assert blocks[1].block_open_time_ns == START + BLOCK_NS
    assert by_index(blocks[1])[10].buy == 7


@pytest.mark.trace("REQ-WP-089")
def test_a_block_is_written_once_and_a_late_trade_for_it_is_discarded_and_counted() -> None:
    made, blocks = builder()
    made.add(trade("a", "100", "1", "buy", at_ns=START + SECOND_NS))
    close(made)
    assert len(blocks) == 1

    made.add(trade("late", "100", "9", "buy", at_ns=START + 2 * SECOND_NS))
    close(made, after_block=1)

    assert len(blocks) == 2
    assert by_index(blocks[0])[10].buy == 1
    assert made.late_trades == 1
    # Nor does it turn up in the block that was open when it arrived.
    assert by_index(blocks[1])[10].buy == 1


@pytest.mark.trace("REQ-WP-089")
def test_the_same_trades_in_any_order_within_the_grace_period_give_the_same_block() -> None:
    trades = [
        trade(
            str(i),
            str(100 + (i * 7) % 30),
            str(i + 1),
            "buy" if i % 2 else "sell",
            at_ns=START + (i + 1) * SECOND_NS,
        )
        for i in range(12)
    ]
    first, first_blocks = builder()
    for t in trades:
        first.add(t)
    close(first)
    shuffled = list(trades)
    random.Random(3).shuffle(shuffled)
    second, second_blocks = builder()
    for t in shuffled:
        second.add(t)
    close(second)

    assert first_blocks[0].bins == second_blocks[0].bins


@pytest.mark.trace("REQ-WP-089")
def test_a_block_waits_out_the_grace_period_before_it_closes() -> None:
    """A trade 1 s past the end does not close the block; one at the end of the grace does."""
    made, blocks = builder()
    made.add(trade("a", "100", "1", "buy", at_ns=START + SECOND_NS))

    made.add(trade("b", "100", "1", "buy", at_ns=START + BLOCK_NS + SECOND_NS))
    assert blocks == []

    made.add(trade("c", "100", "1", "buy", at_ns=START + BLOCK_NS + 5 * SECOND_NS))
    assert len(blocks) == 1


@pytest.mark.trace("REQ-WP-089")
def test_a_block_that_is_still_forming_is_not_written() -> None:
    made, blocks = builder()
    made.add(trade("a", "100", "1", "buy", at_ns=START + SECOND_NS))

    assert blocks == []


@pytest.mark.trace("REQ-WP-089")
def test_a_block_whose_ids_show_missed_trades_is_dropped_and_counted_for_a_sequential_venue() -> (
    None
):
    """Ids 1,2,4,5 are four trades over a span of five: one was missed."""
    made, blocks = builder(sequential_ids=True)
    for i, id_ in enumerate(["1", "2", "4", "5"]):
        made.add(trade(id_, "100", "1", "buy", at_ns=START + (i + 1) * SECOND_NS))
    close(made)

    assert blocks == []
    assert made.incomplete_blocks == 1


@pytest.mark.trace("REQ-WP-089")
def test_a_complete_block_of_a_sequential_venue_and_any_block_of_another_are_written() -> None:
    ok, ok_blocks = builder(sequential_ids=True)
    for i, id_ in enumerate(["1", "2", "3"]):
        ok.add(trade(id_, "100", "1", "buy", at_ns=START + (i + 1) * SECOND_NS))
    close(ok)
    other, other_blocks = builder(sequential_ids=False)
    for i, id_ in enumerate(["1", "2", "4", "5"]):
        other.add(trade(id_, "100", "1", "buy", at_ns=START + (i + 1) * SECOND_NS))
    close(other)

    assert len(ok_blocks) == 1 and ok.incomplete_blocks == 0
    assert len(other_blocks) == 1


@pytest.mark.trace("REQ-WP-089")
def test_ids_that_are_not_numbers_cannot_be_checked_and_do_not_drop_a_block() -> None:
    made, blocks = builder(sequential_ids=True)
    made.add(trade("abc", "100", "1", "buy", at_ns=START + SECOND_NS))
    close(made)

    assert len(blocks) == 1


@pytest.mark.trace("REQ-WP-089")
def test_the_width_is_derived_from_the_first_trades_price_and_kept() -> None:
    made, blocks = builder(width=None)
    made.add(trade("a", "85000", "1", "buy", at_ns=START + SECOND_NS))
    made.add(trade("b", "1", "1", "buy", at_ns=START + 2 * SECOND_NS))
    close(made)

    assert blocks[0].bin_width == Decimal("20")


@pytest.mark.trace("REQ-WP-089")
@pytest.mark.parametrize(
    ("price", "expected"),
    [("85000", "20"), ("2700", "0.5"), ("150", "0.02"), ("1", "0.0002"), ("0.5", "0.0001")],
)
def test_the_default_width_is_two_basis_points_of_the_price_rounded_to_one_two_or_five(
    price: str, expected: str
) -> None:
    assert nice_bin_width(Decimal(price)) == Decimal(expected)


@pytest.mark.trace("REQ-WP-089")
def test_the_widths_configuration_is_read_per_symbol_and_refuses_what_is_wrong_by_name() -> None:
    assert parse_bin_widths("") == {}
    assert parse_bin_widths("binance:BTCUSDT=20, okx:BTC-USDT-SWAP=0.5") == {
        ("binance", "BTCUSDT"): Decimal("20"),
        ("okx", "BTC-USDT-SWAP"): Decimal("0.5"),
    }
    for bad in (
        "binance:BTCUSDT",
        "BTCUSDT=20",
        "binance:BTCUSDT=abc",
        "binance:BTCUSDT=0",
        "binance:BTCUSDT=-1",
    ):
        with pytest.raises(ValueError, match=bad.split("=")[0].split(":")[-1]):
            parse_bin_widths(bad)
    with pytest.raises(ValueError, match="twice"):
        parse_bin_widths("binance:BTCUSDT=20,binance:BTCUSDT=10")
