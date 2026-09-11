"""Dataset identity: what a content hash covers, and what it must not.

REQ-STORE-001, PRD §29.B ("dataset lineage/snapshot reproducibility"),
PRD §0 item 13, [[ADR-053]].
"""

from __future__ import annotations

import io

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from channelflow.lakehouse import (
    Column,
    IcebergTable,
    Schema,
)

from .conftest import trade, trades_schema


def _plane() -> object:
    """A plane of its own.

    These tests compare identities across *separate* planes on purpose: the
    claim is that the same rows get the same identity wherever they were
    written, and sharing one catalog would make that true for a reason nobody
    cares about.
    """
    import tempfile

    from channelflow.lakehouse import catalog as open_catalog

    home = tempfile.mkdtemp(prefix="channelflow-identity-")
    return open_catalog(uri=f"sqlite:///{home}/catalog.db", warehouse=home)


@pytest.mark.trace("REQ-STORE-001")
def test_the_same_rows_get_the_same_identity_in_a_different_store() -> None:
    """PRD §0 item 13 wants a result reproducible from a versioned dataset. That
    is only worth anything if the same data has the same version wherever it is
    written."""
    rows = [trade(1), trade(2)]

    first = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane()).append(rows)
    second = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane()).append(rows)

    assert first.content_hash == second.content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_changing_one_value_changes_the_identity() -> None:
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane())
    original = table.append([trade(1)])

    changed = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane()).append(
        [{**trade(1), "price": 50_000.01}]
    )

    assert changed.content_hash != original.content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_the_parquet_footer_really_does_carry_the_writer_version() -> None:
    """The evidence behind the test above, kept next to it.

    If a future Parquet writer stopped embedding its version, hashing file bytes
    would become defensible and [[ADR-053]] would deserve revisiting. This test
    is what would notice.
    """
    buffer = io.BytesIO()
    pq.write_table(pa.table({"a": pa.array([1], pa.int64())}), buffer)

    assert b"parquet-cpp-arrow version" in buffer.getvalue()


@pytest.mark.trace("REQ-STORE-001")
def test_reordering_the_columns_is_a_different_schema() -> None:
    """Order is part of the physical layout. A table whose columns were reordered
    is a different table to read, and calling it the same one would line up the
    wrong values with the right names."""
    forward = Schema(columns=(Column(name="a", type="int64"), Column(name="b", type="string")))
    reversed_ = Schema(columns=(Column(name="b", type="string"), Column(name="a", type="int64")))

    assert forward.fingerprint != reversed_.fingerprint


@pytest.mark.trace("REQ-STORE-001")
def test_the_event_time_column_is_part_of_the_schema_identity() -> None:
    """Two tables with identical columns, one of which can answer a
    point-in-time read and one of which cannot, are not interchangeable."""
    columns = (Column(name="event_time_ns", type="timestamp_ns"),)

    assert (
        Schema(columns=columns).fingerprint
        != Schema(columns=columns, event_time_column="event_time_ns").fingerprint
    )


@pytest.mark.trace("REQ-STORE-001")
def test_two_types_that_print_the_same_do_not_hash_the_same() -> None:
    """A type tag per value, so an integer 1, a boolean true and the string "1"
    can never be confused by a digest."""
    as_int = Schema(columns=(Column(name="v", type="int64"),)).encode_row({"v": 1})
    as_bool = Schema(columns=(Column(name="v", type="bool"),)).encode_row({"v": True})
    as_text = Schema(columns=(Column(name="v", type="string"),)).encode_row({"v": "1"})

    assert len({as_int, as_bool, as_text}) == 3


@pytest.mark.trace("REQ-STORE-001")
def test_a_value_cannot_forge_a_column_boundary() -> None:
    """Length-prefixed, not separated.

    With a separator, `("ab", "c")` and `("a", "bc")` encode identically as soon
    as a value contains the separator -- and two different datasets share an
    identity.
    """
    schema = Schema(
        columns=(Column(name="left", type="string"), Column(name="right", type="string"))
    )

    assert schema.encode_row({"left": "ab", "right": "c"}) != schema.encode_row(
        {"left": "a", "right": "bc"}
    )


@pytest.mark.trace("REQ-STORE-001")
def test_negative_zero_is_not_zero() -> None:
    """They compare equal and are distinct bit patterns, and Parquet stores them
    distinctly. Hashing them alike would let a file change without its identity
    changing -- the conservative reading is the right one for an identity."""
    schema = Schema(columns=(Column(name="v", type="float64"),))

    assert schema.encode_row({"v": -0.0}) != schema.encode_row({"v": 0.0})


@pytest.mark.trace("REQ-STORE-001")
def test_each_snapshot_in_a_chain_has_its_own_identity() -> None:
    """Appending changes the dataset, so it has to change the dataset's name."""
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane())

    first = table.append([trade(1)])
    second = table.append([trade(2)])

    assert first.content_hash != second.content_hash
    assert table.snapshot(1).content_hash == first.content_hash


@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.trace("REQ-WP-039")
def test_the_identity_covers_the_schema() -> None:
    """Two datasets holding the same values under different columns are two
    datasets.

    Found when the old format was deleted: its hash mixed the schema
    fingerprint in and the first Iceberg version did not, so a run could have
    cited the wrong dataset and still verified.
    """
    rows = [
        {
            "event_time_ns": 1,
            "symbol": "BTCUSDT",
            "price": 1.0,
            "size": 1.0,
            "buyer_is_maker": False,
        }
    ]

    one = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane()).append(rows)
    widened = Schema(
        columns=(*trades_schema().columns, Column(name="venue", type="string")),
        event_time_column="event_time_ns",
    )
    other = IcebergTable(name="cex_trades", schema=widened, catalog=_plane()).append(
        [{**rows[0], "venue": "binance"}]
    )

    assert one.content_hash != other.content_hash


@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.trace("REQ-WP-039")
def test_the_identity_does_not_depend_on_the_bytes_of_the_file() -> None:
    """[[ADR-053]]'s rule, on the new layout.

    The same rows split across a different number of commits produce different
    Parquet files and the same identity.
    """
    rows = [trade(1), trade(2)]

    once = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane()).append(rows)
    apart = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=_plane())
    apart.append([rows[0]])
    twice = apart.append([rows[1]])

    assert once.content_hash == twice.content_hash
