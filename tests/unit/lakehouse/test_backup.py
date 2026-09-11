"""A backup is a claim about restoring, so these tests restore (REQ-WP-037).

The interruption tests are the ones that check the ordering, because a completed
copy is complete whatever order it went in.

They do not, however, distinguish the walk from the obvious implementation --
list every key under the table prefix and copy it. `data/` sorts before
`metadata/`, so that implementation copies data first and is safe for this key
layout. The mutation sweep established this by surviving, and it is recorded
here rather than papered over: the walk is preferred because it satisfies the
ordering by construction, not because the listing is broken today.
"""

from __future__ import annotations

import pytest

from channelflow.lakehouse import (
    BackupConflict,
    Column,
    InMemoryObjectStore,
    Schema,
    Table,
    TargetNotEmpty,
    WouldLandShort,
    back_up,
    restore,
    verify,
)
from channelflow.lakehouse.table import NoSuchSnapshot

from .conftest import trade, trades_schema


class Interrupting:
    """A target that accepts a fixed number of writes and then stops.

    Not a failure injection for its own sake: an interrupted backup is the state
    the ordering rule exists for, and a suite that only ever completes the copy
    cannot tell a correct implementation from one that copies manifests first.
    """

    def __init__(self, allow: int) -> None:
        self.inner = InMemoryObjectStore()
        self.allow = allow
        self.written = 0

    def put(self, key: str, body: bytes) -> None:
        self._budget()
        self.inner.put(key, body)

    def put_if_absent(self, key: str, body: bytes) -> None:
        self._budget()
        self.inner.put_if_absent(key, body)

    def get(self, key: str) -> bytes:
        return self.inner.get(key)

    def list(self, prefix: str) -> list[str]:
        return self.inner.list(prefix)

    def _budget(self) -> None:
        if self.written >= self.allow:
            raise KeyboardInterrupt("the operator went home")
        self.written += 1


def filled(store: InMemoryObjectStore, commits: int = 3) -> Table:
    table = Table(name="cex_trades", schema=trades_schema(), store=store)
    for commit in range(commits):
        table.append([trade(commit * 10 + row) for row in range(3)])
    return table


def without(store: InMemoryObjectStore, key: str) -> InMemoryObjectStore:
    """The same store, missing one object.

    Built by copying rather than by deleting: the port has no `delete`, and it
    should not grow one for a test. This is also the honest shape of the
    scenario -- a copy that lost a file, not a store somebody deleted from.
    """
    copy = InMemoryObjectStore()
    for present in store.list(""):
        if present != key:
            copy.put(present, store.get(present))
    return copy


def opened(store: object) -> Table:
    return Table(name="cex_trades", schema=trades_schema(), store=store)  # type: ignore[arg-type]


# --- the round trip -----------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_a_backed_up_table_restores_row_for_row() -> None:
    """What somebody actually wanted back.

    Asserted on rows rather than digests: a digest check proves the manifests
    agree with the files, and the rows are the thing.
    """
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source)

    back_up("cex_trades", source=source, target=target)
    restore("cex_trades", source=target, target=home)

    assert opened(home).read().to_pylist() == table.read().to_pylist()


@pytest.mark.trace("REQ-WP-037")
def test_the_restored_table_keeps_the_same_snapshot_identity() -> None:
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source)

    back_up("cex_trades", source=source, target=target)
    restore("cex_trades", source=target, target=home)

    restored = opened(home).current()
    original = table.current()
    assert restored is not None and original is not None
    assert restored.content_hash == original.content_hash


@pytest.mark.trace("REQ-WP-037")
def test_a_table_nobody_ever_committed_to_restores_as_one() -> None:
    """Not an error, and not an empty first snapshot -- which would be a commit
    that never happened."""
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    Table(name="cex_trades", schema=trades_schema(), store=source)

    back_up("cex_trades", source=source, target=target)
    report = restore("cex_trades", source=target, target=home)

    assert report.landed_on is None
    assert opened(home).snapshot_ids() == ()


# --- the ordering rule --------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_an_interrupted_backup_never_leaves_a_manifest_over_absent_data() -> None:
    """The ordering rule, at every point the copy could stop.

    `table.py` writes data before the manifest naming it, because orphan files
    are invisible to readers while a manifest naming absent files is corruption.
    This walks every interruption point and asserts the copy never reaches the
    forbidden state.

    It does not distinguish the walk from a key listing, which sorts `data/`
    before `metadata/` and is therefore also safe here -- see the module
    docstring. It does distinguish both from any implementation that writes a
    manifest before what it names.
    """
    source = InMemoryObjectStore()
    filled(source, commits=3)
    complete = back_up("cex_trades", source=source, target=InMemoryObjectStore())

    for budget in range(1, complete.objects):
        target = Interrupting(allow=budget)
        with pytest.raises(KeyboardInterrupt):
            back_up("cex_trades", source=source, target=target)

        report = verify("cex_trades", store=target.inner)
        assert report.missing == (), f"after {budget} write(s): {report.missing}"


@pytest.mark.trace("REQ-WP-037")
def test_an_interrupted_backup_restores_to_its_last_complete_snapshot() -> None:
    source, home = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=3)
    target = Interrupting(allow=4)

    with pytest.raises(KeyboardInterrupt):
        back_up("cex_trades", source=source, target=target)

    report = restore("cex_trades", source=target.inner, target=home, snapshot_id=None)
    assert report.landed_on is not None
    assert opened(home).read().num_rows > 0


@pytest.mark.trace("REQ-WP-037")
def test_re_running_an_interrupted_backup_completes_it() -> None:
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=3)

    partial = Interrupting(allow=3)
    with pytest.raises(KeyboardInterrupt):
        back_up("cex_trades", source=source, target=partial)
    for key in partial.inner.list(""):
        target.put(key, partial.inner.get(key))

    back_up("cex_trades", source=source, target=target)

    assert verify("cex_trades", store=target).ok


# --- where you landed ---------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_a_restore_says_which_snapshot_it_landed_on() -> None:
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=3)

    back_up("cex_trades", source=source, target=target)
    report = restore("cex_trades", source=target, target=home)

    assert report.landed_on == 3
    assert report.newest_available == 3


@pytest.mark.trace("REQ-WP-037")
def test_landing_short_without_being_asked_is_refused() -> None:
    """Restoring to an earlier point is a real request; arriving there by
    accident is indistinguishable from it afterwards.

    The detectable shape of "short" is a backup whose newest *manifest* is not
    its newest *restorable* snapshot -- the manifest is there and a file it
    names is not. A backup this module produced can never look like that, which
    is the point of the ordering rule; a damaged one can, and a restore that
    quietly landed on 2 while the copy claimed 3 would be silent data loss.
    """
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source, commits=3)
    back_up("cex_trades", source=source, target=target)
    newest = table.snapshot(3)
    short = without(target, newest.files[0].key)

    with pytest.raises(WouldLandShort):
        restore("cex_trades", source=short, target=home)


@pytest.mark.trace("REQ-WP-037")
def test_landing_short_is_allowed_when_it_was_asked_for() -> None:
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=3)
    back_up("cex_trades", source=source, target=target)

    report = restore("cex_trades", source=target, target=home, snapshot_id=2)

    assert report.landed_on == 2
    assert opened(home).snapshot_ids() == (1, 2)


@pytest.mark.trace("REQ-WP-037")
def test_asking_for_a_snapshot_the_backup_does_not_hold_is_refused() -> None:
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)

    with pytest.raises(NoSuchSnapshot):
        restore("cex_trades", source=target, target=home, snapshot_id=9)


# --- never merged -------------------------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_restoring_into_a_non_empty_target_is_refused() -> None:
    """Merging two lineages under one version sequence produces a history that
    never existed. Idempotent means restoring twice is safe, not that two
    histories can be blended."""
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=2)
    filled(home, commits=1)
    back_up("cex_trades", source=source, target=target)

    with pytest.raises(TargetNotEmpty):
        restore("cex_trades", source=target, target=home)


@pytest.mark.trace("REQ-WP-037")
def test_two_restores_into_fresh_targets_agree() -> None:
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)

    one, other = InMemoryObjectStore(), InMemoryObjectStore()
    restore("cex_trades", source=target, target=one)
    restore("cex_trades", source=target, target=other)

    assert opened(one).read().to_pylist() == opened(other).read().to_pylist()


# --- three failures, told apart -----------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_a_clean_copy_verifies() -> None:
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)

    current = table.current()
    assert current is not None
    report = verify("cex_trades", store=target, expect_content_hash=current.content_hash)

    assert report.ok
    assert report.identity_ok


@pytest.mark.trace("REQ-WP-037")
def test_a_missing_file_is_reported_as_missing() -> None:
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)
    current = table.current()
    assert current is not None
    damaged = without(target, current.files[0].key)

    report = verify("cex_trades", store=damaged)

    assert report.missing == (current.files[0].key,)
    assert report.corrupt == ()
    assert not report.ok


@pytest.mark.trace("REQ-WP-037")
def test_damage_in_transit_is_reported_as_corrupt_not_missing() -> None:
    """Different answers to the 3am question: one means retry, one does not."""
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)
    current = table.current()
    assert current is not None
    target.put(current.files[0].key, b"not parquet any more")

    report = verify("cex_trades", store=target)

    assert report.corrupt == (current.files[0].key,)
    assert report.missing == ()


@pytest.mark.trace("REQ-WP-037")
def test_a_different_dataset_is_an_identity_failure() -> None:
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)

    report = verify("cex_trades", store=target, expect_content_hash="0" * 64)

    assert not report.identity_ok
    assert report.missing == ()
    assert report.corrupt == ()


@pytest.mark.trace("REQ-WP-037")
def test_an_orphan_object_is_not_a_failure() -> None:
    """The writer already tolerates orphans -- a reader only ever opens files a
    manifest lists. A backup inventing a stricter rule would report corruption
    where the system deliberately accepts waste."""
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=2)
    back_up("cex_trades", source=source, target=target)
    target.put("cex_trades/data/orphan.parquet", b"nobody names me")

    assert verify("cex_trades", store=target).ok


@pytest.mark.trace("REQ-WP-037")
def test_a_hole_in_the_history_is_found_even_when_the_latest_commit_is_whole() -> None:
    """A manifest is cumulative, so the newest one already names every data
    file. What it does not cover is the history behind it.

    With the middle manifest gone, the latest read still works and every
    point-in-time read before it is broken -- which is the whole reason the
    plane keeps a history. The check follows each snapshot's parent for exactly
    this case.
    """
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=3)
    back_up("cex_trades", source=source, target=target)
    damaged = without(target, "cex_trades/metadata/v00000002.json")

    report = verify("cex_trades", store=damaged)

    assert report.missing == ("cex_trades/metadata/v00000002.json",)
    assert not report.ok


@pytest.mark.trace("REQ-WP-037")
def test_a_hole_deep_in_the_history_is_found_too() -> None:
    """The previous test only reaches one link back.

    Checking the newest snapshot's parent alone catches a hole next to the
    latest commit and misses every older one -- the mutation sweep found exactly
    that gap. With five commits and the second manifest gone, snapshot 5's
    parent is present and the break is three links further down.
    """
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=5)
    back_up("cex_trades", source=source, target=target)
    damaged = without(target, "cex_trades/metadata/v00000002.json")

    assert verify("cex_trades", store=damaged).missing == ("cex_trades/metadata/v00000002.json",)


@pytest.mark.trace("REQ-WP-037")
def test_copying_an_object_that_is_already_there_writes_nothing() -> None:
    """What makes an interrupted backup resumable rather than a fresh copy."""
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    filled(source, commits=2)

    first = back_up("cex_trades", source=source, target=target)
    again = back_up("cex_trades", source=source, target=target)

    assert first.objects > 0
    assert again.objects == 0


@pytest.mark.trace("REQ-WP-037")
def test_a_key_already_holding_something_else_is_refused_not_overwritten() -> None:
    """Two backups of different tables under one name, or a half-copied object
    from another source, are both bugs that an overwrite would hide."""
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source, commits=1)
    current = table.current()
    assert current is not None
    target.put(current.files[0].key, b"something else entirely")

    with pytest.raises(BackupConflict):
        back_up("cex_trades", source=source, target=target)


@pytest.mark.trace("REQ-WP-037")
def test_one_absent_file_is_one_finding_however_many_manifests_name_it() -> None:
    """Cumulative manifests mean a file from the first commit is named by every
    later one. Four lines for one problem buries the other three."""
    source, target = InMemoryObjectStore(), InMemoryObjectStore()
    table = filled(source, commits=4)
    back_up("cex_trades", source=source, target=target)
    first = table.snapshot(1).files[0].key
    damaged = without(target, first)

    assert verify("cex_trades", store=damaged).missing == (first,)


# --- the table is not the copier ----------------------------------------------


@pytest.mark.trace("REQ-WP-037")
def test_a_schema_free_table_backs_up_too() -> None:
    """A backup works on keys, not rows, so a table with no event time is no
    different -- and nothing about the schema is consulted."""
    source, target, home = InMemoryObjectStore(), InMemoryObjectStore(), InMemoryObjectStore()
    schema = Schema(columns=(Column(name="key", type="string"),))
    Table(name="market_config", schema=schema, store=source).append([{"key": "a"}])

    back_up("market_config", source=source, target=target)
    restore("market_config", source=target, target=home)

    assert Table(name="market_config", schema=schema, store=home).read().num_rows == 1
