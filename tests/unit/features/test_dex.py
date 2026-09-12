"""PRD §18A.4's directional swap imbalance (REQ-WP-059)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.domain import ChainMeta, DexSwapEvent, EventMeta
from channelflow.features.dex import FEATURES, swap_imbalance
from channelflow.features.registry import REGISTRY

SECOND_NS = 1_000_000_000
NOW = 1_700_000_060 * SECOND_NS
MINUTE_NS = 60 * SECOND_NS


def _swap(*, amount0: str, at_ns: int, log_index: int = 0) -> DexSwapEvent:
    return DexSwapEvent(
        meta=EventMeta(
            source="evm-logs",
            venue="uniswap",
            market_type="spot",
            symbol="WETH/USDC",
            event_time_ns=at_ns,
            ingest_time_ns=at_ns + 1_000,
        ),
        chain=ChainMeta(
            chain_id=1,
            block_number=21_000_000,
            block_time_ns=at_ns,
            tx_hash="0xabc",
            tx_index=1,
            log_index=log_index,
        ),
        dex="uniswap_v3",
        pool="0xpool",
        token0="WETH",
        token1="USDC",
        amount0=Decimal(amount0),
        # Not read by this feature, and deliberately not made to agree with
        # amount0: a test that kept them consistent could not tell which one the
        # arithmetic used.
        amount1=Decimal("1"),
        price_token1_per_token0=Decimal("3000"),
    )


@pytest.mark.trace("REQ-WP-059")
def test_the_imbalance_is_the_signed_flow_over_the_gross_flow() -> None:
    swaps = [
        _swap(amount0="3", at_ns=NOW - 10 * SECOND_NS, log_index=0),
        _swap(amount0="-1", at_ns=NOW - 5 * SECOND_NS, log_index=1),
    ]
    window = swap_imbalance(swaps, as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.signed == Decimal("2")
    assert window.gross == Decimal("4")
    assert window.value == Decimal("0.5")


@pytest.mark.trace("REQ-WP-059")
def test_one_sided_windows_reach_the_bounds() -> None:
    selling = [_swap(amount0="2", at_ns=NOW - 1, log_index=i) for i in range(3)]
    assert swap_imbalance(selling, as_of_ns=NOW, window_ns=MINUTE_NS).value == Decimal(1)

    buying = [_swap(amount0="-2", at_ns=NOW - 1, log_index=i) for i in range(3)]
    assert swap_imbalance(buying, as_of_ns=NOW, window_ns=MINUTE_NS).value == Decimal(-1)


@pytest.mark.trace("REQ-WP-059")
def test_a_balanced_window_reads_zero() -> None:
    """Zero is a reading about a busy window, and it has to be reachable."""
    swaps = [
        _swap(amount0="5", at_ns=NOW - 3 * SECOND_NS, log_index=0),
        _swap(amount0="-5", at_ns=NOW - 2 * SECOND_NS, log_index=1),
    ]
    window = swap_imbalance(swaps, as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.value == Decimal(0)
    assert window.directional_swaps == 2


@pytest.mark.trace("REQ-WP-059")
def test_an_empty_window_has_no_imbalance() -> None:
    """The distinction the whole feature turns on: silence is not balance."""
    window = swap_imbalance([], as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.value is None
    assert window.swaps == 0
    assert window.gross == Decimal(0)


@pytest.mark.trace("REQ-WP-059")
def test_a_swap_that_moved_no_token0_is_counted_but_has_no_direction() -> None:
    """Measured on chain 999: two of eighty-three swaps report a zero side."""
    swaps = [
        _swap(amount0="4", at_ns=NOW - 3 * SECOND_NS, log_index=0),
        _swap(amount0="0", at_ns=NOW - 2 * SECOND_NS, log_index=1),
    ]
    window = swap_imbalance(swaps, as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.swaps == 2
    assert window.directional_swaps == 1
    assert window.gross == Decimal(4)
    assert window.value == Decimal(1), "the zero swap did not dilute the imbalance"


@pytest.mark.trace("REQ-WP-059")
def test_a_window_of_only_zero_swaps_has_no_imbalance() -> None:
    swaps = [_swap(amount0="0", at_ns=NOW - 1, log_index=i) for i in range(3)]
    window = swap_imbalance(swaps, as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.swaps == 3
    assert window.directional_swaps == 0
    assert window.value is None


@pytest.mark.trace("REQ-WP-059")
def test_the_window_is_half_open_at_the_floor_and_closed_at_the_cursor() -> None:
    floor = NOW - MINUTE_NS
    swaps = [
        _swap(amount0="1", at_ns=floor, log_index=0),
        _swap(amount0="10", at_ns=floor + 1, log_index=1),
        _swap(amount0="100", at_ns=NOW, log_index=2),
    ]
    window = swap_imbalance(swaps, as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.directional_swaps == 2
    assert window.gross == Decimal(110), "the swap at the floor is outside"


@pytest.mark.trace("REQ-WP-059")
def test_a_swap_after_the_cursor_is_not_visible() -> None:
    """Constitution Principle I, on the only arithmetic that could break it."""
    swaps = [
        _swap(amount0="1", at_ns=NOW - SECOND_NS, log_index=0),
        _swap(amount0="-1000", at_ns=NOW + 1, log_index=1),
    ]
    window = swap_imbalance(swaps, as_of_ns=NOW, window_ns=MINUTE_NS)
    assert window.swaps == 1
    assert window.value == Decimal(1)


@pytest.mark.trace("REQ-WP-059")
def test_a_window_spanning_nothing_is_refused() -> None:
    for span in (0, -1):
        with pytest.raises(ValueError, match="spans nothing"):
            swap_imbalance([], as_of_ns=NOW, window_ns=span)


@pytest.mark.trace("REQ-WP-059")
def test_the_feature_is_registered_and_says_what_it_is() -> None:
    assert FEATURES == ("dex_swap_imbalance",)
    spec = REGISTRY["dex_swap_imbalance"]
    assert spec.family == "defi"
    assert spec.source_events == ("dex_swap",)
    assert spec.point_in_time_safe is True
    assert "zero is the reading for a balanced window" in spec.null_policy
    assert "amount0" in spec.formula


@pytest.mark.trace("REQ-WP-059")
def test_no_usd_denominated_swap_feature_is_registered() -> None:
    """`notional_usd` is set by nothing, so a USD flow feature would be absent
    on every swap -- indistinguishable, on a pane, from a quiet market."""
    assert not [name for name in REGISTRY if name.startswith("dex_swap_") and "usd" in name]
