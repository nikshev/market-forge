"""The snapshot chain: immutable, atomic, and readable only when committed.

REQ-STORE-001, PRD §29.B.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.lakehouse import (
    CommitRaceLost,
    InMemoryObjectStore,
    NoSuchSnapshot,
    SchemaMismatch,
    Table,
)

from .conftest import config_schema, trade, trades_schema


@pytest.mark.trace("REQ-STORE-001")
def test_appending_leaves_every_earlier_snapshot_exactly_as_it_was(trades: Table) -> None:
    """PRD §29.B's snapshots are immutable, and PRD §0 item 5 says the same thing
    one level up: "do not rewrite historical channel snapshots or signal
    snapshots after they are finalized".

    Here it is a property of the key space rather than a discipline -- a manifest
    is written under a key naming its own version and nothing rewrites it -- so
    this test is what proves the key space actually behaves that way.
    """
    first = trades.append([trade(1), trade(2)])
    recorded = (first.content_hash, first.files, first.record_count)

    trades.append([trade(3)])

    reread = trades.snapshot(first.snapshot_id)
    assert (reread.content_hash, reread.files, reread.record_count) == recorded


@pytest.mark.trace("REQ-STORE-001")
def test_a_read_at_a_snapshot_ignores_everything_appended_since(trades: Table) -> None:
    """The storage-level form of "as seen then". A research run pinned to a
    snapshot has to keep seeing what it saw, or its result stops being about
    anything."""
    trades.append([trade(1), trade(2)])
    trades.append([trade(3), trade(4), trade(5)])

    assert trades.read(snapshot_id=1).num_rows == 2
    assert trades.read().num_rows == 5


@pytest.mark.trace("REQ-STORE-001")
def test_the_chain_records_its_own_order(trades: Table) -> None:
    first = trades.append([trade(1)])
    second = trades.append([trade(2)])

    assert first.parent_id is None
    assert second.parent_id == first.snapshot_id
    assert trades.snapshot_ids() == (1, 2)


class RacingStore:
    """A store that loses the first commit race, deterministically.

    A real race needs two writers that both read the same current snapshot and
    then both try to commit the next version. Sequentially that cannot happen --
    the second writer re-reads and picks a later version -- so the collision has
    to be injected at the only instant it can occur: between computing the
    version and writing its manifest.

    This wrapper installs the rival's objects at exactly that instant, so the
    conditional write that follows finds the key already taken.
    """

    def __init__(self, inner: InMemoryObjectStore, rival: dict[str, bytes]) -> None:
        self._inner = inner
        self._rival = rival
        self.raced = False

    def put(self, key: str, body: bytes) -> None:
        self._inner.put(key, body)

    def put_if_absent(self, key: str, body: bytes) -> None:
        if not self.raced:
            self.raced = True
            for rival_key, rival_body in self._rival.items():
                self._inner.put(rival_key, rival_body)
        self._inner.put_if_absent(key, body)

    def get(self, key: str) -> bytes:
        return self._inner.get(key)

    def list(self, prefix: str) -> list[str]:
        return self._inner.list(prefix)


def _rival_commit(store: InMemoryObjectStore, table: Table) -> dict[str, bytes]:
    """What a second writer's version-2 commit would put in the store."""
    sibling = InMemoryObjectStore()
    for key in store.list(""):
        sibling.put(key, store.get(key))
    Table(name=table.name, schema=table.schema, store=sibling).append([trade(99)])
    return {key: sibling.get(key) for key in sibling.list("") if key not in set(store.list(""))}


@pytest.mark.trace("REQ-STORE-001")
def test_a_commit_that_loses_the_race_leaves_the_table_where_it_was(
    store: InMemoryObjectStore,
) -> None:
    """Two writers, one version number.

    The loser raises and changes nothing about the table. Its data file is
    already in the store and is unreferenced -- garbage, not corruption, because
    a reader only ever opens files a manifest names.
    """
    trades = Table(name="cex_trades", schema=trades_schema(), store=store)
    trades.append([trade(1)])
    rival_objects = _rival_commit(store, trades)

    racing = Table(
        name="cex_trades",
        schema=trades_schema(),
        store=RacingStore(store, rival_objects),  # type: ignore[arg-type]
    )
    with pytest.raises(CommitRaceLost, match="another writer"):
        racing.append([trade(2)])

    current = trades.current()
    assert current is not None and current.snapshot_id == 2
    referenced = {file.key for sid in trades.snapshot_ids() for file in trades.snapshot(sid).files}
    orphans = {key for key in store.list("cex_trades/data/") if key not in referenced}
    assert len(orphans) == 1, "the losing writer left exactly its own data file behind"
    assert trades.read().num_rows == 2, "and no query can see it"
    assert trade(2)["event_time_ns"] not in trades.read()["event_time_ns"].to_pylist()


@pytest.mark.trace("REQ-STORE-001")
def test_a_data_file_without_a_manifest_is_not_a_snapshot(
    trades: Table, store: InMemoryObjectStore
) -> None:
    """ "No partially written snapshot is readable", made true by construction: a
    snapshot exists exactly when its manifest does."""
    trades.append([trade(1)])
    store.put("cex_trades/data/00000002/deadbeef.parquet", b"not even parquet")

    assert trades.snapshot_ids() == (1,)
    assert trades.read().num_rows == 1


@pytest.mark.trace("REQ-STORE-001")
def test_an_append_of_no_rows_is_refused(trades: Table) -> None:
    """It would commit a snapshot identical to its parent under a new id, and
    everything keyed by snapshot would see a change that did not happen."""
    with pytest.raises(ValueError, match="did not happen"):
        trades.append([])


@pytest.mark.trace("REQ-STORE-001")
def test_an_append_under_a_different_schema_is_refused(
    trades: Table, store: InMemoryObjectStore
) -> None:
    """One snapshot chain, one shape.

    A snapshot names its schema and its files are read under it; a chain
    carrying two would make "read this snapshot" ambiguous at the file that
    changed.
    """
    trades.append([trade(1)])
    widened = Table(name=trades.name, schema=config_schema(), store=store)

    with pytest.raises(SchemaMismatch):
        widened.append([{"key": "tick", "value": "0.01"}])


@pytest.mark.trace("REQ-STORE-001")
def test_an_earlier_snapshot_still_reads_under_the_schema_it_was_written_with(
    trades: Table,
) -> None:
    """A schema is versioned by its fingerprint, and every snapshot records the
    one it was committed with."""
    first = trades.append([trade(1)])

    assert first.schema_fingerprint == trades_schema().fingerprint
    assert trades.snapshot(1).schema_fingerprint == first.schema_fingerprint


@pytest.mark.trace("REQ-STORE-001")
def test_a_table_nothing_has_committed_to_has_no_snapshot(trades: Table) -> None:
    """`None`, not an empty snapshot. A table that has never been written to and
    a table whose latest commit holds no rows are different facts, and only the
    second one has a content hash."""
    assert trades.current() is None
    assert trades.snapshot_ids() == ()

    empty = trades.read()
    assert empty.num_rows == 0
    assert empty.schema.names == list(trades.schema.names)


@pytest.mark.trace("REQ-STORE-001")
def test_a_read_of_a_snapshot_that_was_never_committed_is_refused(trades: Table) -> None:
    trades.append([trade(1)])

    with pytest.raises(NoSuchSnapshot, match="cex_trades"):
        trades.snapshot(7)


@pytest.mark.trace("REQ-STORE-001")
def test_the_recorded_event_time_is_the_batch_maximum(trades: Table) -> None:
    """Not a commit time -- nothing here reads a clock, so there is none to
    record."""
    first = trades.append([trade(1), trade(5), trade(3)])

    assert first.event_time_max_ns == trade(5)["event_time_ns"]


@pytest.mark.trace("REQ-STORE-001")
def test_a_table_with_no_event_time_reports_none(config: Table) -> None:
    """Zero, and stated as such: a table without an event-time column has no
    event time, and inventing one from a clock is what this package refuses."""
    first = config.append([{"key": "tick", "value": "0.01"}])

    assert first.event_time_max_ns == 0


@pytest.mark.trace("REQ-STORE-001")
def test_nothing_in_the_lakehouse_consults_a_clock() -> None:
    """Every timestamp it records comes from the data.

    A manifest stamped with wall-clock time would make two replays of the same
    stream produce different manifests, and therefore different bytes, for data
    that is identical -- which is the property Principle XI exists to protect.
    """
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "lakehouse"
    modules = sorted(package.glob("*.py"))
    assert modules, "the lakehouse package has no modules; this test would pass vacuously"
    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"


@pytest.mark.trace("REQ-STORE-001")
def test_two_tables_over_one_store_are_the_same_table(
    trades: Table, store: InMemoryObjectStore
) -> None:
    """`Table` is frozen and stateless on purpose: everything about the table
    lives in the store, so no instance can hold a view that goes stale behind
    another."""
    trades.append([trade(1)])
    other = Table(name=trades.name, schema=trades.schema, store=store)

    assert other.snapshot_ids() == trades.snapshot_ids()
    assert other.read().num_rows == trades.read().num_rows


@pytest.mark.trace("REQ-STORE-001")
def test_the_tenth_commit_does_not_reorder_the_chain(trades: Table) -> None:
    """Nine commits is not a chain; the boundary is where an ordering bug hides.

    `snapshot_ids` parses each version and sorts the integers, so this passes
    with or without the zero-padding in the key -- a mutation removing the
    padding changed nothing here, which is how that was established rather than
    assumed. What this test does cover is everything else that could go wrong
    once the chain is longer than a single digit: the accumulating file list,
    the parent links, and reading every file the newest manifest names.
    """
    for index in range(1, 12):
        trades.append([trade(index)])

    assert trades.snapshot_ids() == tuple(range(1, 12))
    current = trades.current()
    assert current is not None and current.snapshot_id == 11
    assert trades.read().num_rows == 11


@pytest.mark.trace("REQ-STORE-001")
def test_container_columns_survive_the_round_trip(store: InMemoryObjectStore) -> None:
    """PRD §29.6 asks a channel snapshot for forecast arrays and quality
    components by name, so the plane has to carry both without a child table."""
    from channelflow.lakehouse import Column, Schema

    schema = Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="horizons", type="float_list"),
            Column(name="contributing", type="string_list"),
            Column(name="submetrics", type="float_map"),
        ),
        event_time_column="event_time_ns",
    )
    table = Table(name="channel_snapshots", schema=schema, store=store)
    table.append(
        [
            {
                "event_time_ns": 1,
                "horizons": [1.5, 2.5],
                "contributing": ["fit", "width"],
                "submetrics": {"fit": 0.9, "age": 0.1},
            }
        ]
    )

    row = table.read().to_pylist()[0]
    assert row["horizons"] == [1.5, 2.5]
    assert row["contributing"] == ["fit", "width"]
    assert dict(row["submetrics"]) == {"age": 0.1, "fit": 0.9}


@pytest.mark.trace("REQ-STORE-001")
def test_an_empty_container_is_stored_as_empty_and_not_as_absent(
    store: InMemoryObjectStore,
) -> None:
    """Baseline A produces no forecast horizons at all, and PRD §13.7's note
    says fabricating a plausible list would be worse than an honest absence. An
    empty list has to come back empty rather than as null."""
    from channelflow.lakehouse import Column, Schema

    schema = Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="horizons", type="float_list"),
        ),
        event_time_column="event_time_ns",
    )
    table = Table(name="t", schema=schema, store=store)
    table.append([{"event_time_ns": 1, "horizons": []}])

    assert table.read().to_pylist()[0]["horizons"] == []
