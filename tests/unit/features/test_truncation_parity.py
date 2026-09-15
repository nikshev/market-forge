"""PRD §35.4: every feature answers the same on a truncated and a full input.

    For every feature:
      1. Run on truncated dataset through `t`.
      2. Run on full dataset but ask for feature at `t`.
      3. Values must match exactly within numeric tolerance.
      This should be an automated CI suite.

**Why this is worth the work.** `FeatureSpec` carries
`point_in_time_safe: Literal[True]`, so the type makes any other value
unregisterable: all 55 registered features *declare* point-in-time safety, and
the only test that touches that field asserts it is a `bool` — which the type
guarantees before the test runs. The promise is extracted by the type and
verified by nothing. This is its verification.

**`NOT_YET_COVERED` is a debt register, not a permission.** The 55 features share
no interface — some take events with a window, some a book service, some a
stateful tracker — so each case is written by hand against its own signature.
[[REQ-NRT-LEAK]] stays at `specified` until that list is empty. What the list
*does* buy: a feature added tomorrow lands in `uncovered()` and not in the
literal, so the suite goes red by name rather than the gap widening quietly.
"""

from __future__ import annotations

import pytest

from channelflow.bars import Bar
from channelflow.channels import RollingOLSChannel
from channelflow.channels.features import (
    channel_position,
    channel_quality_score,
    channel_slope_normalized,
    channel_width_pct,
)
from channelflow.features import REGISTRY, exposed_feature_names
from channelflow.features.truncation import (
    RELATIVE_TOLERANCE,
    Refusal,
    TruncationCase,
    divergence,
    uncovered,
)
from tests.unit.channels.conftest import log_linear_series

LOOKBACK = 30
BARS = 90
#: The moment every case asks about: far enough in that the model has its whole
#: lookback, far enough from the end that a real future exists to leak from.
AT_INDEX = 60


def _snapshot(bars: list[Bar], *, upto: int | None, at_index: int):
    """Fit at `bars[at_index]`, seeing either the prefix or everything."""
    series = bars if upto is None else bars[:upto]
    return RollingOLSChannel(lookback=LOOKBACK).fit(
        list(series), as_of_ns=bars[at_index].close_time_ns
    )


def _channel_cases() -> list[TruncationCase]:
    bars = log_linear_series(BARS)
    at_ns = bars[AT_INDEX].close_time_ns
    price = float(bars[AT_INDEX].close)
    readers = {
        "channel_slope_normalized": channel_slope_normalized,
        "channel_width_pct": channel_width_pct,
        "channel_quality_score": channel_quality_score,
    }
    cases = [
        TruncationCase(
            feature=name,
            at_ns=at_ns,
            truncated=lambda reader=reader: reader(
                _snapshot(bars, upto=AT_INDEX + 1, at_index=AT_INDEX)
            ),
            full=lambda reader=reader: reader(_snapshot(bars, upto=None, at_index=AT_INDEX)),
        )
        for name, reader in readers.items()
    ]
    cases.append(
        TruncationCase(
            feature="channel_position",
            at_ns=at_ns,
            truncated=lambda: channel_position(
                _snapshot(bars, upto=AT_INDEX + 1, at_index=AT_INDEX), price
            ),
            full=lambda: channel_position(_snapshot(bars, upto=None, at_index=AT_INDEX), price),
        )
    )
    return cases


CASES: list[TruncationCase] = _channel_cases()

REFUSALS: list[Refusal] = []

#: Registered features with neither a case nor a refusal. This list is debt and
#: must only shrink. REQ-NRT-LEAK cannot reach `implemented` while it is
#: non-empty.
NOT_YET_COVERED: frozenset[str] = frozenset(
    name for name in exposed_feature_names() if REGISTRY[name].family != "channel"
)


# --- the enumeration --------------------------------------------------------


@pytest.mark.trace("REQ-NRT-LEAK")
def test_the_registry_is_fully_imported_before_anything_is_counted() -> None:
    """`REGISTRY` reaches 27 if only `channelflow.features.*` is imported.

    Three further packages register features. `exposed_feature_names()` imports
    all eight, and is therefore the enumeration -- counting the other way looks
    complete and is half.
    """
    names = exposed_feature_names()
    assert len(names) == 55
    assert sorted(names) == sorted(REGISTRY)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_every_registered_feature_is_covered_or_declared_outstanding() -> None:
    """A feature added tomorrow is red by name, not a quietly widening gap."""
    assert uncovered(REGISTRY, CASES, REFUSALS) == NOT_YET_COVERED, (
        "a registered feature has neither a truncation case nor a refusal, and is "
        "not in NOT_YET_COVERED -- add a case, or add it to the debt register"
    )


@pytest.mark.trace("REQ-NRT-LEAK")
def test_the_debt_register_is_what_stops_this_requirement_completing() -> None:
    assert len(NOT_YET_COVERED) == 51
    assert len(CASES) == 4
    assert {case.feature for case in CASES} == {
        "channel_position",
        "channel_quality_score",
        "channel_slope_normalized",
        "channel_width_pct",
    }


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_case_for_an_unregistered_feature_is_refused() -> None:
    """Otherwise a typo in a feature name reads as coverage."""
    stray = TruncationCase(
        feature="no_such_feature", at_ns=1, truncated=lambda: 1.0, full=lambda: 1.0
    )
    with pytest.raises(KeyError, match="no_such_feature"):
        uncovered(REGISTRY, [*CASES, stray], REFUSALS)


# --- the parity itself ------------------------------------------------------


@pytest.mark.trace("REQ-NRT-LEAK")
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.feature)
def test_the_truncated_and_full_runs_agree(case: TruncationCase) -> None:
    found = divergence(case)
    assert found is None, str(found)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_the_case_actually_computes_something() -> None:
    """A case whose two sides both raise, or both return None, proves nothing."""
    for case in CASES:
        value = case.truncated()
        assert value is not None, f"{case.feature} produced nothing to compare"
        assert isinstance(value, float)


# --- the fault, introduced on purpose ---------------------------------------


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_leaking_feature_is_caught_and_names_both_values() -> None:
    """A feature that reads a later row answers differently on the full input."""
    bars = log_linear_series(BARS)
    leaking = TruncationCase(
        feature="channel_width_pct",
        at_ns=bars[AT_INDEX].close_time_ns,
        truncated=lambda: float(bars[AT_INDEX].close),
        # The leak: it reads a bar after `t`.
        full=lambda: float(bars[BARS - 1].close),
    )
    found = divergence(leaking)
    assert found is not None, "a feature reading the future went unnoticed"
    assert found.feature == "channel_width_pct"
    assert found.truncated == float(bars[AT_INDEX].close)
    assert found.full == float(bars[BARS - 1].close)
    assert "channel_width_pct" in str(found)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_difference_inside_the_tolerance_is_not_a_divergence() -> None:
    base = 1_000.0
    case = TruncationCase(
        feature="channel_width_pct",
        at_ns=1,
        truncated=lambda: base,
        full=lambda: base * (1 + RELATIVE_TOLERANCE / 2),
    )
    assert divergence(case) is None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_difference_outside_the_tolerance_is_a_divergence() -> None:
    base = 1_000.0
    case = TruncationCase(
        feature="channel_width_pct",
        at_ns=1,
        truncated=lambda: base,
        full=lambda: base * (1 + RELATIVE_TOLERANCE * 10),
    )
    assert divergence(case) is not None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_two_large_integers_one_apart_are_not_the_same_answer() -> None:
    """A relative tolerance applied to integers would call these equal.

    `10**12` and `10**12 + 1` differ by 1e-12 relative -- inside any float
    tolerance worth having, and a whole unit of whatever the feature counts.
    """
    case = TruncationCase(
        feature="channel_width_pct",
        at_ns=1,
        truncated=lambda: 10**12,
        full=lambda: 10**12 + 1,
    )
    assert divergence(case) is not None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_an_integer_and_an_equal_float_are_different_answers() -> None:
    """`5` and `5.0` are equal in Python and are not the same value here."""
    case = TruncationCase(
        feature="channel_width_pct", at_ns=1, truncated=lambda: 5, full=lambda: 5.0
    )
    assert divergence(case) is not None


@pytest.mark.trace("REQ-NRT-LEAK")
def test_integers_and_none_compare_exactly() -> None:
    """Tolerance is for floating point. An integer that moved by one has moved."""
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: 5, full=lambda: 6
            )
        )
        is not None
    )
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: 5, full=lambda: 5
            )
        )
        is None
    )
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: None, full=lambda: None
            )
        )
        is None
    )
    assert (
        divergence(
            TruncationCase(
                feature="channel_width_pct", at_ns=1, truncated=lambda: None, full=lambda: 0.0
            )
        )
        is not None
    )


@pytest.mark.trace("REQ-NRT-LEAK")
@pytest.mark.parametrize("blank", ["", "   ", "\t", "\n  "])
def test_a_refusal_has_to_give_a_reason(blank: str) -> None:
    """Whitespace is not a reason. A refusal without one is a skip, renamed."""
    with pytest.raises(ValueError, match="reason"):
        Refusal(feature="channel_width_pct", reason=blank)


@pytest.mark.trace("REQ-NRT-LEAK")
def test_a_refusal_covers_the_feature_it_names() -> None:
    """Otherwise the debt register and the refusals disagree about the same name."""
    outstanding = sorted(NOT_YET_COVERED)[0]
    refusal = Refusal(feature=outstanding, reason="a reason long enough to be one")
    still_open = uncovered(REGISTRY, CASES, [refusal])
    assert outstanding not in still_open
    assert still_open == NOT_YET_COVERED - {outstanding}
