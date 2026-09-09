"""What a schema refuses, and why each refusal is not pedantry.

REQ-STORE-001, PRD §29.0.
"""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Column, Schema, UnknownColumn

from .conftest import trades_schema


@pytest.mark.trace("REQ-STORE-001")
def test_a_row_missing_a_column_is_refused() -> None:
    """A missing value written as a default would say "none" where it means
    "unknown", and the content hash would agree with both -- so two datasets
    that differ in what was measured would share an identity."""
    schema = trades_schema()

    with pytest.raises(UnknownColumn, match="missing"):
        schema.encode_row({"event_time_ns": 1, "symbol": "BTCUSDT"})


@pytest.mark.trace("REQ-STORE-001")
def test_a_row_carrying_a_column_the_schema_does_not_declare_is_refused() -> None:
    """Silently dropping it would write a file that does not hold what the
    caller passed, and nothing downstream could tell."""
    schema = Schema(columns=(Column(name="a", type="int64"),))

    with pytest.raises(UnknownColumn, match="stray"):
        schema.encode_row({"a": 1, "stray": 2})


@pytest.mark.trace("REQ-STORE-001")
def test_duplicate_columns_are_refused() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        Schema(columns=(Column(name="a", type="int64"), Column(name="a", type="string")))


@pytest.mark.trace("REQ-STORE-001")
def test_a_schema_with_no_columns_is_refused() -> None:
    with pytest.raises(ValueError, match="at least one column"):
        Schema(columns=())


@pytest.mark.trace("REQ-STORE-001")
def test_an_event_time_column_has_to_be_a_nanosecond_count() -> None:
    """A point-in-time filter compares integers. Pointing it at a string column
    would compare text and answer plausibly."""
    with pytest.raises(ValueError, match="nanosecond"):
        Schema(
            columns=(Column(name="when", type="string"),),
            event_time_column="when",
        )


@pytest.mark.trace("REQ-STORE-001")
def test_an_event_time_column_that_does_not_exist_is_refused() -> None:
    with pytest.raises(UnknownColumn, match="missing_column"):
        Schema(
            columns=(Column(name="a", type="int64"),),
            event_time_column="missing_column",
        )


@pytest.mark.trace("REQ-STORE-001")
def test_a_column_type_outside_the_vocabulary_is_refused() -> None:
    """The vocabulary is closed so two writers cannot disagree about what a
    column is."""
    with pytest.raises(ValueError, match="storage types"):
        Column(name="a", type="decimal")  # type: ignore[arg-type]


@pytest.mark.trace("REQ-STORE-001")
def test_a_value_of_the_wrong_python_type_is_refused() -> None:
    """Coercion here would be silent and lossy: `int("1.9")` raises, `int(1.9)`
    does not, and the second is how a price becomes a different price."""
    schema = Schema(
        columns=(
            Column(name="count", type="int64"),
            Column(name="price", type="float64"),
            Column(name="flag", type="bool"),
            Column(name="name", type="string"),
        )
    )
    valid: dict[str, object] = {"count": 1, "price": 1.0, "flag": True, "name": "x"}

    for field, wrong in (
        ("count", "1"),
        ("price", "1.0"),
        ("flag", 1),
        ("name", 1),
    ):
        with pytest.raises(TypeError):
            schema.encode_row({**valid, field: wrong})


@pytest.mark.trace("REQ-STORE-001")
def test_a_boolean_is_not_an_integer() -> None:
    """Python says `True == 1` and `isinstance(True, int)`. A schema that agreed
    would let a flag column accept counts and a count column accept flags, and
    the type tag in the digest would then be the only thing left telling them
    apart -- after the value had already been written wrong."""
    counts = Schema(columns=(Column(name="v", type="int64"),))
    flags = Schema(columns=(Column(name="v", type="bool"),))

    with pytest.raises(TypeError):
        counts.encode_row({"v": True})
    with pytest.raises(TypeError):
        flags.encode_row({"v": 1})


@pytest.mark.trace("REQ-STORE-001")
def test_an_integer_is_accepted_where_a_float_is_declared() -> None:
    """The one coercion that is safe and worth having: every integer is exactly
    representable as a float64, so `50000` and `50000.0` are the same value and
    hash the same."""
    schema = Schema(columns=(Column(name="v", type="float64"),))

    assert schema.encode_row({"v": 50_000}) == schema.encode_row({"v": 50_000.0})


@pytest.mark.trace("REQ-STORE-001")
def test_a_column_is_reachable_by_name_and_an_unknown_one_is_not() -> None:
    schema = trades_schema()

    assert schema.column("price").type == "float64"
    with pytest.raises(UnknownColumn, match="nope"):
        schema.column("nope")
