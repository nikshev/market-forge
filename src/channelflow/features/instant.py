"""Features of one book state (PRD sections 15.1 and 15.2).

# @trace: REQ-WP-011

No history and no windows: each of these is a function of the book as it is
right now, which is what makes them the easiest to check by hand and the
hardest to get subtly wrong.

Every one goes through `BookService`'s reads, so PRD section 11.1 rule 6 --
never emit a feature from an invalid book -- holds without any function here
remembering it.
"""

from __future__ import annotations

from decimal import Decimal

from channelflow.book import BookInvalid, BookService
from channelflow.features.registry import FeatureSpec, register

#: Names exposed by this module. `exposed_feature_names` reads it, and the
#: registry test fails on anything here without an entry below.
FEATURES: tuple[str, ...] = (
    "qi_l1",
    "depth_imbalance_5",
    "depth_imbalance_10",
    "depth_imbalance_20",
    "depth_imbalance_50",
    "depth_imbalance_bps_5",
    "depth_imbalance_bps_10",
    "depth_imbalance_bps_25",
    "depth_imbalance_bps_50",
    "microprice",
    "microprice_mid_spread_bps",
)

#: PRD section 15.1's level counts and distance bands.
LEVEL_DEPTHS: tuple[int, ...] = (1, 5, 10, 20, 50)
BPS_BANDS: tuple[int, ...] = (5, 10, 25, 50)


def _imbalance(bid: Decimal, ask: Decimal) -> float:
    """PRD section 15.1's ratio, with the one case it cannot answer.

    A zero denominator is not a balanced book; it is a book with nothing
    resting on either side of the comparison, which carries no imbalance
    information at all. Returning 0.0 would be indistinguishable downstream
    from a genuinely balanced touch.
    """
    total = bid + ask
    if total == 0:
        raise BookInvalid(
            "no resting size on either side: an imbalance ratio would divide by "
            "zero, and reporting 0.0 would read as a balanced book"
        )
    return float((bid - ask) / total)


def queue_imbalance(service: BookService) -> float:
    """`(bid_qty - ask_qty) / (bid_qty + ask_qty)` at the touch (section 15.1)."""
    bids, asks = service.top(1)
    if not bids or not asks:
        raise BookInvalid(
            "one side of the book is empty: there is no opposite queue to compare the other against"
        )
    return _imbalance(bids[0].qty, asks[0].qty)


def depth_imbalance_levels(service: BookService, levels: int) -> float:
    """Section 15.1's `DI_k` over the top `levels` rungs of each side."""
    bids, asks = service.top(levels)
    if not bids or not asks:
        raise BookInvalid("one side of the book is empty: no depth to compare")
    return _imbalance(
        sum((level.qty for level in bids), Decimal(0)),
        sum((level.qty for level in asks), Decimal(0)),
    )


def depth_imbalance_bps(service: BookService, bps: float) -> float:
    """Section 15.1's fixed distance bands, measured from the mid (ADR-011)."""
    bid_depth, ask_depth = service.depth_within_bps(bps)
    return _imbalance(bid_depth, ask_depth)


def microprice(service: BookService) -> Decimal:
    """Best bid and ask weighted by the *opposite* queue (section 15.2).

    Opposite, not same. A large ask queue is sellers waiting in line, and the
    price a taker will actually get is nearer the bid -- so the big queue
    pushes the price away from itself. Weighting by the same side gives the
    mid whenever the queues are equal too, which is why the balanced case
    alone cannot tell the two formulas apart.
    """
    bids, asks = service.top(1)
    if not bids or not asks:
        raise BookInvalid("one side of the book is empty: no queue to weight by")
    bid, ask = bids[0], asks[0]
    total = bid.qty + ask.qty
    if total == 0:
        raise BookInvalid("both touches are empty: nothing to weight the prices by")
    return (bid.price * ask.qty + ask.price * bid.qty) / total


def microprice_mid_spread_bps(service: BookService) -> float:
    """How far the microprice sits from the mid, in basis points (section 15.2)."""
    mid = service.mid()
    return float((microprice(service) - mid) / mid * Decimal(10_000))


def _register_all() -> None:
    register(
        FeatureSpec(
            name="qi_l1",
            version=1,
            family="order_book",
            description="Queue imbalance at the touch.",
            formula="(bid_qty_l1 - ask_qty_l1) / (bid_qty_l1 + ask_qty_l1)",
            unit="normalized",
            source_events=("book_snapshot", "book_delta"),
            lookback="instant",
            cadence="per book update",
            availability_lag_ms=0,
            null_policy="refuses when either touch is empty or both are zero-sized",
            clipping="none; the ratio is bounded to [-1, 1] by construction",
            normalization="none; already a ratio",
            point_in_time_safe=True,
            test_fixture="tests/unit/features/test_instant.py::test_queue_imbalance_at_the_touch",
        )
    )
    for levels in LEVEL_DEPTHS:
        if levels == 1:
            continue  # qi_l1 is this same ratio at the touch
        register(
            FeatureSpec(
                name=f"depth_imbalance_{levels}",
                version=1,
                family="order_book",
                description=f"Depth imbalance over the top {levels} levels per side.",
                formula=f"(sum_bid_depth_{levels} - sum_ask_depth_{levels}) / total_depth_{levels}",
                unit="normalized",
                source_events=("book_snapshot", "book_delta"),
                lookback="instant",
                cadence="per book update",
                availability_lag_ms=0,
                null_policy="refuses when either side is empty",
                clipping="none; bounded to [-1, 1] by construction",
                normalization="none; already a ratio",
                point_in_time_safe=True,
                test_fixture=(
                    "tests/unit/features/test_instant.py"
                    "::test_depth_imbalance_deepens_as_more_levels_are_counted"
                ),
            )
        )
    for bps in BPS_BANDS:
        register(
            FeatureSpec(
                name=f"depth_imbalance_bps_{bps}",
                version=1,
                family="order_book",
                description=f"Depth imbalance within +/-{bps} bps of the mid.",
                formula=(
                    f"(bid_depth_within_{bps}bps - ask_depth_within_{bps}bps) / their sum; "
                    "distance measured from the mid price (ADR-011)"
                ),
                unit="normalized",
                source_events=("book_snapshot", "book_delta"),
                lookback="instant",
                cadence="per book update",
                availability_lag_ms=0,
                null_policy="refuses when no mid price exists or the band holds nothing",
                clipping="none; bounded to [-1, 1] by construction",
                normalization="none; already a ratio",
                point_in_time_safe=True,
                test_fixture=(
                    "tests/unit/features/test_instant.py"
                    "::test_a_band_imbalance_reflects_lopsided_depth"
                ),
            )
        )
    register(
        FeatureSpec(
            name="microprice",
            version=1,
            family="order_book",
            description="Best bid and ask weighted by the opposite queue size.",
            formula="(bid_price * ask_qty + ask_price * bid_qty) / (bid_qty + ask_qty)",
            unit="quote currency",
            source_events=("book_snapshot", "book_delta"),
            lookback="instant",
            cadence="per book update",
            availability_lag_ms=0,
            null_policy="refuses when either touch is empty",
            clipping="none",
            normalization="none; a price in quote currency",
            point_in_time_safe=True,
            test_fixture=(
                "tests/unit/features/test_instant.py"
                "::test_the_microprice_leans_away_from_the_larger_queue"
            ),
        )
    )
    register(
        FeatureSpec(
            name="microprice_mid_spread_bps",
            version=1,
            family="order_book",
            description="Distance from the microprice to the mid, in basis points.",
            formula="(microprice - mid) / mid * 10_000",
            unit="basis points",
            source_events=("book_snapshot", "book_delta"),
            lookback="instant",
            cadence="per book update",
            availability_lag_ms=0,
            null_policy="refuses when the microprice or the mid does not exist",
            clipping="none",
            normalization="expressed relative to the mid, so comparable across prices",
            point_in_time_safe=True,
            test_fixture=(
                "tests/unit/features/test_instant.py"
                "::test_the_microprice_mid_spread_is_reported_in_basis_points"
            ),
        )
    )


_register_all()
