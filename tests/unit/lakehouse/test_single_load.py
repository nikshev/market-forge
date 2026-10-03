"""A snapshot read resolves its snapshot against the table it reads (REQ-WP-079).

On 2026-10-02/03 the worker and the resample job logged `NoSuchSnapshot: bars has no snapshot
4424; it has (1, 2, 3, ...)` fourteen times in thirteen hours. A read loaded the table, asked for
the list of snapshots with a *second* load to learn which was newest, and resolved that number
against the first. Five writers commit to the `bars` table; a commit between the two loads names a
snapshot the first has never heard of.

Nothing in the single-process lakehouse tests could see it, because nothing committed between two
loads. These tests make a commit land there on every call (`racing.py`), so the fault shows on the
first call instead of the thousandth. Those that pass today by design say so.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import Any

import pytest

from channelflow.lakehouse import Catalog, IcebergTable
from channelflow.lakehouse.iceberg import NoSuchSnapshot

from .conftest import trade, trades_schema
from .racing import CountingCatalog, RacingCatalog

COMMITS = 4
READS = 25  # SC-001: one race is already a proof; 25 guard against order luck


def _handle(catalog: Any) -> IcebergTable:
    return IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)


def _seeded(catalog: Catalog) -> IcebergTable:
    """A table with COMMITS commits, written through the plain catalog."""
    writer = _handle(catalog)
    for index in range(1, COMMITS + 1):
        writer.append([trade(index)])
    return writer


# --- User Story 1: one load per operation -------------------------------------------------

OPERATIONS: dict[str, Callable[[IcebergTable], object]] = {
    "snapshot_ids()": lambda t: t.snapshot_ids(),
    "read()": lambda t: t.read(),
    "read(snapshot_id=2)": lambda t: t.read(snapshot_id=2),
    "current()": lambda t: t.current(),
    "snapshot(2)": lambda t: t.snapshot(2),
    "append([row])": lambda t: t.append([trade(1000)]),
}


@pytest.mark.trace("REQ-WP-079")
@pytest.mark.parametrize("operation", list(OPERATIONS))
def test_each_public_operation_loads_the_table_once(catalog: Catalog, operation: str) -> None:
    """Every extra load is a chance for another process's commit to land between two of them.
    Fails today with 2, 2, 5, 5 and 7 loads."""
    _seeded(catalog)
    counting = CountingCatalog(catalog)
    reader = _handle(counting)

    OPERATIONS[operation](reader)

    assert counting.total == 1, f"{operation} loaded the table {counting.total} times"


@pytest.mark.trace("REQ-WP-079")
@pytest.mark.parametrize("operation", ["read()", "current()"])
def test_the_newest_snapshot_survives_a_commit_between_loads(
    catalog: Catalog, operation: str
) -> None:
    """The deployment's fault, made to happen on every call: after the first load each further one
    is preceded by another process's commit.

    `read()` fails today with `NoSuchSnapshot` -- the log's own message. `current()` does **not**:
    it takes the newest number from the *first* load and looks it up in later ones, which can only
    have more snapshots, so it survives the race by the direction of its mistake. Its fault is
    the five loads (the count test above), and it is here to stay passing. Planning had said it
    was exposed to the same error; running it showed it was not."""
    writer = _seeded(catalog)
    numbers = itertools.count(2000)
    racing = RacingCatalog(catalog, lambda: writer.append([trade(next(numbers))]))
    reader = _handle(racing)

    for _ in range(READS):
        racing.arm()
        result = OPERATIONS[operation](reader)
        assert result is not None
    # No assertion that a competing commit happened: with one load per call there is no second
    # load to precede, so none does. That is the fix working, and the load-count test above is
    # what stops this one going vacuous -- a second load put back brings the race, and a failure.


@pytest.mark.trace("REQ-WP-079")
def test_describing_a_snapshot_by_number_survives_a_commit_between_loads(
    catalog: Catalog,
) -> None:
    """Passes today as far as the *error* goes -- a pinned number exists in every later version --
    and is here for the claim in FR-003 that no other load can make it vanish. What it adds over
    the load count is the behaviour: the description is of the snapshot asked for."""
    writer = _seeded(catalog)
    numbers = itertools.count(3000)
    racing = RacingCatalog(catalog, lambda: writer.append([trade(next(numbers))]))
    reader = _handle(racing)

    for _ in range(READS):
        newest = writer.snapshot_ids()[-1]
        racing.arm()
        described = reader.snapshot(newest)
        assert described.snapshot_id == newest


@pytest.mark.trace("REQ-WP-079")
def test_append_returns_the_snapshot_it_wrote_not_the_newest_when_it_returns(
    catalog: Catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-009. `append` described `snapshot_ids()[-1]` from a *fresh* load after its commit, so a
    competitor that committed a moment later became the answer, with no error to say so. Here the
    competing commit lands immediately after this writer's own. Also pins the library behaviour the
    fix relies on: pyiceberg refreshes `table.metadata` at its own commit."""
    from pyiceberg.table import Table

    writer = _seeded(catalog)
    before = writer.snapshot_ids()[-1]
    rows_before = writer.read().num_rows
    competitor = _handle(catalog)
    real_append = Table.append
    state = {"inside": False}

    def append_then_compete(self: Table, df: Any, *args: Any, **kwargs: Any) -> None:
        real_append(self, df, *args, **kwargs)
        if not state["inside"]:
            state["inside"] = True
            competitor.append([trade(5000)])
            state["inside"] = False

    monkeypatch.setattr(Table, "append", append_then_compete)

    returned = writer.append([trade(4000)])

    assert returned.snapshot_id == before + 1, "it returned a snapshot someone else wrote"
    assert returned.record_count == rows_before + 1, "its count includes the competitor's row"
    assert writer.snapshot_ids()[-1] == before + 2, "the competitor did commit, after it"


# --- User Story 2: pinned reads stay reproducible and honest --------------------------------


@pytest.mark.trace("REQ-WP-079")
def test_a_pinned_read_returns_the_same_rows_after_later_commits(catalog: Catalog) -> None:
    """A regression guard: green before the change and required to stay green (FR-005)."""
    writer = _seeded(catalog)
    before = writer.read(snapshot_id=2).to_pylist()

    for index in range(10, 14):
        writer.append([trade(index)])

    assert writer.read(snapshot_id=2).to_pylist() == before


@pytest.mark.trace("REQ-WP-079")
def test_a_table_nothing_has_been_committed_to_reads_empty(catalog: Catalog) -> None:
    """A regression guard (FR-006): green before the change."""
    table = _handle(catalog)

    assert table.read().num_rows == 0
    assert table.current() is None
    assert table.snapshot_ids() == ()


@pytest.mark.trace("REQ-WP-079")
@pytest.mark.parametrize("operation", ["read", "snapshot"])
def test_a_snapshot_the_table_does_not_have_is_still_refused(
    catalog: Catalog, operation: str
) -> None:
    """A regression guard (FR-004): green before the change. The fix must not turn a missing
    snapshot into an empty answer or a newer one."""
    table = _seeded(catalog)

    with pytest.raises(NoSuchSnapshot) as raised:
        if operation == "read":
            table.read(snapshot_id=1000)
        else:
            table.snapshot(1000)

    assert "has no snapshot 1000" in str(raised.value)


@pytest.mark.trace("REQ-WP-079")
@pytest.mark.parametrize("operation", ["read", "snapshot"])
def test_the_refusal_lists_the_snapshots_of_the_version_that_was_read(
    catalog: Catalog, operation: str
) -> None:
    """FR-004's second half. Today the message is built from a *later* load, so it names snapshots
    the lookup that failed never saw -- and a reader debugging the fault is told a list that was
    not the one searched. Fails today for that reason."""
    writer = _seeded(catalog)
    numbers = itertools.count(6000)
    racing = RacingCatalog(catalog, lambda: writer.append([trade(next(numbers))]))
    reader = _handle(racing)
    version_read = tuple(writer.snapshot_ids())

    racing.arm()
    with pytest.raises(NoSuchSnapshot) as raised:
        if operation == "read":
            reader.read(snapshot_id=1000)
        else:
            reader.snapshot(1000)

    assert f"it has {version_read}" in str(raised.value), str(raised.value)
