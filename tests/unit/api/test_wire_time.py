"""A nanosecond survives the trip to the browser (REQ-WP-061).

PRD §13A.1 requires `extremum_time != known_at`, and the comparisons that
enforce it run in a browser where `number` cannot hold either value.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, ValidationError

from channelflow.api import schemas

#: A real nanosecond mark whose low digits are not a multiple of 256, so that
#: reading it as a double changes it.
EXACT_NS = 1789000000123456789

#: The grid spacing of an IEEE-754 double at that magnitude.
DOUBLE_GRID_NS = 256

#: Every field that is a moment in time. A new one has to be added here, which
#: is the point: the list is the contract, and a field that is a timestamp and
#: not on it is the mistake this whole requirement is about.
TIMESTAMP_FIELDS = {
    ("BarOut", "open_time_ns"),
    ("BarOut", "close_time_ns"),
    ("ChannelOut", "as_of_ns"),
    ("ChannelOut", "source_max_event_time_ns"),
    ("SignalOut", "opened_at_ns"),
    ("TransitionOut", "bar_close_time_ns"),
    ("FeaturePointOut", "at_ns"),
    ("ConfirmedExtremumOut", "extremum_time_ns"),
    ("ConfirmedExtremumOut", "known_at_ns"),
    ("ExtremumCandidateOut", "candidate_time_ns"),
    ("ExtremumCandidateOut", "observed_at_ns"),
    ("FeatureSnapshotResponse", "at_ns"),
    ("DexDepthResponse", "requested_at_ns"),
    ("DexDepthResponse", "state_time_ns"),
}

#: Spans, not moments. Bounded by the timeframes this system supports.
DURATION_FIELDS = {
    ("SignalOut", "timeframe_ns"),
    ("ChannelComparisonOut", "hindsight_ns"),
}


def _models() -> dict[str, type[BaseModel]]:
    """The wire schemas, and only those.

    Defined in this module, not merely visible from it: `schemas.py` imports the
    domain models it converts from -- `Bar`, `ChannelSnapshot`,
    `ConfirmedExtremum` and the rest -- and every one of them has `_ns` fields
    that are correctly `int`, because they never go over a wire. Collecting them
    made the contract check fail on fifteen fields that were right.
    """
    return {
        name: value
        for name, value in vars(schemas).items()
        if isinstance(value, type)
        and issubclass(value, BaseModel)
        and value.__module__ == schemas.__name__
    }


def _ns_fields() -> set[tuple[str, str]]:
    return {
        (name, field)
        for name, model in _models().items()
        for field in model.model_fields
        if field.endswith("_ns")
    }


@pytest.mark.trace("REQ-WP-061")
def test_every_ns_field_is_a_timestamp_or_a_duration() -> None:
    """The guard that keeps this file honest.

    Without it a new `_ns` field could be added as an `int`, be a timestamp, and
    no assertion below would ever look at it.
    """
    assert _ns_fields() == TIMESTAMP_FIELDS | DURATION_FIELDS


@pytest.mark.trace("REQ-WP-061")
def test_timestamps_go_over_the_wire_as_strings() -> None:
    models = _models()
    for name, field in sorted(TIMESTAMP_FIELDS):
        annotation = models[name].model_fields[field].annotation
        assert annotation in {str, str | None}, f"{name}.{field} is {annotation}"


@pytest.mark.trace("REQ-WP-061")
def test_durations_stay_integers_and_fit_in_a_double() -> None:
    """A week is 6.0e14 against a safe maximum of 9.0e15, so a duration needs no
    conversion. Asserted rather than assumed: the bound is what makes the
    distinction legitimate instead of convenient."""
    models = _models()
    for name, field in sorted(DURATION_FIELDS):
        assert models[name].model_fields[field].annotation is int

    week_ns = 7 * 24 * 60 * 60 * 1_000_000_000
    assert week_ns < 2**53 - 1


@pytest.mark.trace("REQ-WP-061")
def test_a_mark_survives_json_exactly_where_a_number_would_not() -> None:
    """The measurement the requirement rests on, as a test."""
    point = schemas.FeaturePointOut(at_ns=str(EXACT_NS), values={"cvd": 1.0})

    restored = json.loads(point.model_dump_json())
    assert int(restored["at_ns"]) == EXACT_NS

    # The same value through a double, which is what a `number` field would have
    # given every consumer.
    through_a_double = int(float(EXACT_NS))
    assert through_a_double != EXACT_NS
    assert abs(through_a_double - EXACT_NS) < DOUBLE_GRID_NS


@pytest.mark.trace("REQ-WP-061")
def test_two_marks_closer_than_the_double_grid_stay_distinct() -> None:
    near, far = EXACT_NS, EXACT_NS + 100

    first = schemas.FeaturePointOut(at_ns=str(near), values={})
    second = schemas.FeaturePointOut(at_ns=str(far), values={})

    assert first.at_ns != second.at_ns
    assert float(near) == float(far), "as numbers they would have been one mark"


@pytest.mark.trace("REQ-WP-061")
def test_an_empty_timestamp_is_refused_rather_than_becoming_the_epoch() -> None:
    """`BigInt("")` in a browser is `0n`. That is 1970: positive, ordered and
    believable, and it would place a bar at the beginning of time."""
    with pytest.raises(ValidationError):
        schemas.FeaturePointOut(at_ns="", values={})


@pytest.mark.trace("REQ-WP-061")
@pytest.mark.parametrize("bad", ["-1", "12.5", "1e9", "abc", " 1789", "1789 ", "0x10", "+5", "007"])
def test_a_timestamp_that_is_not_digits_is_refused(bad: str) -> None:
    """Each of these either throws in `BigInt` -- reaching a reader as a crash in
    a render rather than a stated load failure -- or parses to something else.
    `"007"` is refused because a canonical mark has no leading zeros, so two
    spellings of one instant cannot both be served."""
    with pytest.raises(ValidationError):
        schemas.FeaturePointOut(at_ns=bad, values={})


@pytest.mark.trace("REQ-WP-061")
def test_zero_is_a_valid_mark() -> None:
    """The epoch is refused as an *empty* field and allowed as a stated one:
    what is forbidden is a blank becoming a time, not the time itself."""
    assert schemas.FeaturePointOut(at_ns="0", values={}).at_ns == "0"
