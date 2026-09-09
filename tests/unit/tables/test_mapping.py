"""The row helpers and the mappings, tested where the API cannot reach them.

REQ-STORE-002. Some properties here exist for the content hash or for a reader
that gets rows in another order, and neither is visible through an endpoint.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.signals import Candidate, CandidateState, Transition
from channelflow.tables import features, signals
from channelflow.tables.rows import (
    RowShape,
    as_decimal,
    as_float_map,
    as_float_tuple,
    as_int,
    as_str,
    as_str_tuple,
)

MINUTE_NS = 60 * 1_000_000_000


@pytest.mark.trace("REQ-STORE-002")
def test_a_decimal_column_refuses_anything_but_its_exact_text() -> None:
    """`Decimal(str(1.1))` would accept a float and reintroduce the rounding the
    column type exists to prevent, so the stored value has to already be the
    text it was written as."""
    assert as_decimal({"price": "112000.10"}, "price") == Decimal("112000.10")

    for wrong in (112000.1, 112000, None):
        with pytest.raises(RowShape, match="exact text"):
            as_decimal({"price": wrong}, "price")


@pytest.mark.trace("REQ-STORE-002")
def test_the_row_helpers_refuse_across_kinds() -> None:
    """`int("12")` and `float("1.0")` both succeed on a string. A column that
    returned text where a number belongs is schema drift worth a traceback."""
    with pytest.raises(RowShape):
        as_int({"v": "12"}, "v")
    with pytest.raises(RowShape):
        as_str({"v": 12}, "v")
    with pytest.raises(RowShape):
        as_float_tuple({"v": "abc"}, "v")
    with pytest.raises(RowShape):
        as_str_tuple({"v": "abc"}, "v")
    with pytest.raises(RowShape):
        as_float_map({"v": 1.0}, "v")


@pytest.mark.trace("REQ-STORE-002")
def test_a_boolean_is_not_an_integer_here_either() -> None:
    """Python says `isinstance(True, int)`. A count column that accepted a flag
    would store one and read it back as 1."""
    with pytest.raises(RowShape):
        as_int({"v": True}, "v")


@pytest.mark.trace("REQ-STORE-002")
def test_a_map_column_reads_from_either_shape() -> None:
    """Arrow hands a map back as a list of pairs; a caller that already
    converted one should not have to know which it holds."""
    assert as_float_map({"v": [("a", 1.0)]}, "v") == {"a": 1.0}
    assert as_float_map({"v": {"a": 1.0}}, "v") == {"a": 1.0}


@pytest.mark.trace("REQ-STORE-002")
def test_feature_rows_do_not_depend_on_a_mapping_s_insertion_order() -> None:
    """The rows are what the content hash is taken over. A dataset identity that
    changed with a dict's insertion history would change for a snapshot that did
    not."""
    forward = features.feature_rows(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=1,
        values={"ofi_1m": 0.4, "qi_l1": -0.2},
    )
    backward = features.feature_rows(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        at_ns=1,
        values={"qi_l1": -0.2, "ofi_1m": 0.4},
    )

    assert forward == backward
    assert [row["feature_name"] for row in forward] == ["ofi_1m", "qi_l1"]


@pytest.mark.trace("REQ-STORE-002")
def test_a_transition_history_is_restored_by_its_ordinal() -> None:
    """Not by its bar close time, and not by the order rows happened to arrive.

    Two transitions can share a bar close time -- a touch and a rejection inside
    one bar -- so the close time is not an order. This shuffles the rows to make
    the point: whatever order a reader gets them in, the history is the one that
    happened.
    """
    original = Candidate(
        venue="binance",
        symbol="BTCUSDT",
        timeframe_ns=MINUTE_NS,
        direction="short",
        boundary="upper",
        state=CandidateState.CONFIRMED,
        opened_at_ns=MINUTE_NS,
        bars_since_open=1,
        history=(
            Transition(
                from_state=CandidateState.NONE,
                to_state=CandidateState.APPROACH,
                bar_close_time_ns=MINUTE_NS,
                reason="entered",
            ),
            Transition(
                from_state=CandidateState.APPROACH,
                to_state=CandidateState.TOUCH,
                bar_close_time_ns=MINUTE_NS,
                reason="touched in the same bar",
            ),
            Transition(
                from_state=CandidateState.TOUCH,
                to_state=CandidateState.CONFIRMED,
                bar_close_time_ns=2 * MINUTE_NS,
                reason="confirmed",
            ),
        ),
    )
    core, transitions = signals.to_rows(original)

    restored = signals.from_rows(core, list(reversed(transitions)))

    assert restored == original


@pytest.mark.trace("REQ-STORE-002")
def test_two_different_scores_get_two_different_ids() -> None:
    """A score's contributions join on its id. Two scores sharing one would give
    a score every group either of them had."""
    from channelflow.scoring import Group, GroupContribution, SignalScore

    def make(value: float) -> SignalScore:
        return SignalScore(
            raw=value,
            final=value,
            data_quality=1.0,
            confidence=1.0,
            contributions=(
                GroupContribution(group=Group.ORDER_FLOW, value=value, factors=("ofi",)),
            ),
            missing=(),
        )

    common = {"venue": "binance", "symbol": "BTCUSDT", "as_of_ns": 0, "model_version": "v"}

    assert features.score_id(score=make(1.0), **common) != features.score_id(  # type: ignore[arg-type]
        score=make(2.0),
        **common,  # type: ignore[arg-type]
    )
    assert features.score_id(score=make(1.0), **common) == features.score_id(  # type: ignore[arg-type]
        score=make(1.0),
        **common,  # type: ignore[arg-type]
    )
