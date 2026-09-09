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
    DataFile,
    InMemoryObjectStore,
    ManifestTampered,
    Schema,
    Snapshot,
    Table,
)

from .conftest import trade, trades_schema


def _file(content: str, *, stored: str) -> DataFile:
    return DataFile(
        key="k",
        record_count=1,
        byte_size=1,
        file_sha256=stored,
        content_sha256=content,
    )


def _snapshot(*files: DataFile, fingerprint: str = "fp") -> Snapshot:
    return Snapshot(
        snapshot_id=1,
        parent_id=None,
        schema_fingerprint=fingerprint,
        files=files,
        event_time_max_ns=0,
    )


@pytest.mark.trace("REQ-STORE-001")
def test_the_same_rows_get_the_same_identity_in_a_different_store() -> None:
    """PRD §0 item 13 wants a result reproducible from a versioned dataset. That
    is only worth anything if the same data has the same version wherever it is
    written."""
    rows = [trade(1), trade(2)]

    first = Table(name="cex_trades", schema=trades_schema(), store=InMemoryObjectStore()).append(
        rows
    )
    second = Table(name="cex_trades", schema=trades_schema(), store=InMemoryObjectStore()).append(
        rows
    )

    assert first.content_hash == second.content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_changing_one_value_changes_the_identity() -> None:
    store = InMemoryObjectStore()
    table = Table(name="cex_trades", schema=trades_schema(), store=store)
    original = table.append([trade(1)])

    changed = Table(name="cex_trades", schema=trades_schema(), store=InMemoryObjectStore()).append(
        [{**trade(1), "price": 50_000.01}]
    )

    assert changed.content_hash != original.content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_the_identity_does_not_depend_on_the_bytes_of_the_file() -> None:
    """The decision this whole module exists for ([[ADR-053]]).

    Parquet's footer carries a `created_by` string naming the writer version, so
    the same rows written after a library upgrade are different bytes. A dataset
    identity taken over those bytes would change when nobody changed the data,
    and PRD §0 item 13's reproducibility claim would break on a dependency
    bump.
    """
    same_content = _snapshot(_file("content", stored="written-by-version-a"))
    after_upgrade = _snapshot(_file("content", stored="written-by-version-b"))

    assert same_content.content_hash == after_upgrade.content_hash
    assert same_content.files[0].file_sha256 != after_upgrade.files[0].file_sha256


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
def test_the_identity_covers_the_schema() -> None:
    """Two tables holding the same values under different column names are not
    the same dataset, and a hash that said so would let a rename go unnoticed."""
    files = (_file("content", stored="bytes"),)

    assert (
        _snapshot(*files, fingerprint="one").content_hash
        != _snapshot(*files, fingerprint="two").content_hash
    )


@pytest.mark.trace("REQ-STORE-001")
def test_the_identity_does_not_depend_on_the_order_the_files_are_listed_in() -> None:
    """A snapshot is a set of files, not a sequence of them. Ordering the digests
    keeps the identity from changing when a manifest lists the same files in a
    different order."""
    a, b = _file("aaa", stored="x"), _file("bbb", stored="y")

    assert _snapshot(a, b).content_hash == _snapshot(b, a).content_hash


@pytest.mark.trace("REQ-STORE-001")
def test_a_snapshot_with_no_files_still_has_an_identity() -> None:
    """A table that exists and holds nothing is not the same as one that holds a
    row, and neither is the same as one with other columns."""
    empty_one = _snapshot(fingerprint="one")
    empty_two = _snapshot(fingerprint="two")

    assert empty_one.content_hash != empty_two.content_hash
    assert (
        empty_one.content_hash != _snapshot(_file("c", stored="s"), fingerprint="one").content_hash
    )


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
def test_a_manifest_edited_after_it_was_committed_is_refused() -> None:
    """The manifest records its own content hash as well as its files, so an
    edit that changes one without the other is caught on the next read."""
    snapshot = _snapshot(_file("content", stored="bytes"))
    tampered = snapshot.serialize().replace(
        b'"content_sha256":"content"', b'"content_sha256":"other!!"'
    )

    with pytest.raises(ManifestTampered, match="changed after it was committed"):
        Snapshot.deserialize(tampered)


@pytest.mark.trace("REQ-STORE-001")
def test_a_manifest_whose_counts_are_not_integers_is_refused() -> None:
    """A manifest is JSON something else wrote. Coercing `"12"` into a record
    count is how a truncated read looks like a short table."""
    snapshot = _snapshot(_file("content", stored="bytes"))
    tampered = snapshot.serialize().replace(b'"record_count":1', b'"record_count":"1"')

    with pytest.raises(ManifestTampered, match="record_count"):
        Snapshot.deserialize(tampered)


@pytest.mark.trace("REQ-STORE-001")
def test_a_manifest_survives_a_round_trip() -> None:
    """The control for the two refusals above: an untouched manifest reads back
    as itself, so those tests are about tampering rather than about parsing."""
    snapshot = _snapshot(_file("content", stored="bytes"))

    assert Snapshot.deserialize(snapshot.serialize()) == snapshot


@pytest.mark.trace("REQ-STORE-001")
def test_each_snapshot_in_a_chain_has_its_own_identity() -> None:
    """Appending changes the dataset, so it has to change the dataset's name."""
    table = Table(name="cex_trades", schema=trades_schema(), store=InMemoryObjectStore())

    first = table.append([trade(1)])
    second = table.append([trade(2)])

    assert first.content_hash != second.content_hash
    assert table.snapshot(1).content_hash == first.content_hash
