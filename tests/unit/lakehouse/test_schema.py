"""What a schema refuses, and why each refusal is not pedantry.

REQ-STORE-001, PRD §29.0.
"""

from __future__ import annotations

from decimal import Decimal

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
        Column(name="a", type="numeric")  # type: ignore[arg-type]


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


@pytest.mark.trace("REQ-STORE-001")
def test_a_decimal_column_takes_a_decimal_and_nothing_else() -> None:
    """A price is money. Accepting a float here would let `0.1` in, which
    float64 cannot hold, and the value stored would not be the value passed."""
    schema = Schema(columns=(Column(name="price", type="decimal"),))

    assert schema.encode_row({"price": Decimal("112000.10")})
    for wrong in (112000.1, "112000.10", 112000):
        with pytest.raises(TypeError, match="Decimal"):
            schema.encode_row({"price": wrong})


@pytest.mark.trace("REQ-STORE-001")
def test_two_decimals_that_compare_equal_are_different_content() -> None:
    """`Decimal("1.10")` and `Decimal("1.1")` are equal and carry different
    exponents; Parquet stores the two strings distinctly. A hash calling them the
    same would let a stored value change without its identity changing -- the
    same reading `-0.0` gets."""
    schema = Schema(columns=(Column(name="price", type="decimal"),))

    assert schema.encode_row({"price": Decimal("1.10")}) != schema.encode_row(
        {"price": Decimal("1.1")}
    )


@pytest.mark.trace("REQ-STORE-001")
def test_a_schema_names_the_columns_a_reader_has_to_convert_back() -> None:
    """A caller that forgot one would compare a string against a number and find
    nothing, which reads as an empty result rather than as a mistake."""
    schema = Schema(
        columns=(
            Column(name="open", type="decimal"),
            Column(name="count", type="int64"),
            Column(name="close", type="decimal"),
        )
    )

    assert schema.decimal_columns == ("open", "close")


@pytest.mark.trace("REQ-STORE-001")
def test_a_float_list_hashes_by_its_order() -> None:
    """PRD §29.6's "forecast arrays" are a curve, not a set: the value at horizon
    one is not the value at horizon two."""
    schema = Schema(columns=(Column(name="horizons", type="float_list"),))

    assert schema.encode_row({"horizons": [1.0, 2.0]}) != schema.encode_row(
        {"horizons": [2.0, 1.0]}
    )
    assert schema.encode_row({"horizons": []}) != schema.encode_row({"horizons": [0.0]})


@pytest.mark.trace("REQ-STORE-001")
def test_a_string_list_cannot_forge_its_own_boundaries() -> None:
    """Framed per item, so `["ab"]` and `["a", "b"]` are different values."""
    schema = Schema(columns=(Column(name="names", type="string_list"),))

    assert schema.encode_row({"names": ["ab"]}) != schema.encode_row({"names": ["a", "b"]})


@pytest.mark.trace("REQ-STORE-001")
def test_a_float_map_hashes_the_same_whatever_order_it_was_built_in() -> None:
    """A map is not ordered. Two writers that inserted the same pairs in
    different orders wrote the same value, and an identity that disagreed would
    make a snapshot's hash depend on a dict's insertion history."""
    schema = Schema(columns=(Column(name="submetrics", type="float_map"),))

    assert schema.encode_row({"submetrics": {"a": 1.0, "b": 2.0}}) == schema.encode_row(
        {"submetrics": {"b": 2.0, "a": 1.0}}
    )
    assert schema.encode_row({"submetrics": {"a": 1.0}}) != schema.encode_row(
        {"submetrics": {"a": 2.0}}
    )


@pytest.mark.trace("REQ-STORE-001")
def test_a_container_column_refuses_the_wrong_shape() -> None:
    """A string is a sequence in Python, which is how a name ends up stored as a
    list of its own characters."""
    lists = Schema(columns=(Column(name="v", type="string_list"),))
    maps = Schema(columns=(Column(name="v", type="float_map"),))

    with pytest.raises(TypeError, match="sequence"):
        lists.encode_row({"v": "abc"})
    with pytest.raises(TypeError, match="mapping"):
        maps.encode_row({"v": [("a", 1.0)]})


@pytest.mark.trace("REQ-STORE-001")
def test_a_schema_names_the_map_columns_a_reader_has_to_convert() -> None:
    """Arrow hands a map back as a list of pairs. A reader that forgot one gets
    `[("fit", 0.9)]` where it expected `{"fit": 0.9}`, and the mistake surfaces
    wherever the value is used rather than where it was read."""
    schema = Schema(
        columns=(
            Column(name="submetrics", type="float_map"),
            Column(name="score", type="float64"),
        )
    )

    assert schema.map_columns == ("submetrics",)
