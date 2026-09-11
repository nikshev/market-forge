"""Retention expires by policy, never what a lineage names (REQ-WP-038).

The pass this file tests is the first thing in this system that destroys. Every
other operation appends, so the ways this can go wrong are not the ways the rest
of the code can go wrong -- and the worst of them leaves a table that reads
perfectly and cannot answer a question it could answer yesterday.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pytest

from channelflow.lakehouse import (
    Catalog,
    Column,
    IcebergTable,
    NoEventTime,
    Schema,
    verify,
)
from channelflow.lakehouse.retention import NoSuchPin, RetentionPolicy, apply

SECOND = 1_000_000_000
NOW = 1_000 * SECOND


def trades_schema() -> Schema:
    return Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="symbol", type="string"),
            Column(name="price", type="float64"),
        ),
        event_time_column="event_time_ns",
    )


def row(second: int) -> dict[str, object]:
    return {"event_time_ns": second * SECOND, "symbol": "BTCUSDT", "price": 50_000.0}


def aged(catalog: Catalog) -> IcebergTable:
    """Four commits, one per era: 100s, 300s, 700s and 950s ago."""
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)
    for second in (50, 300, 700, 950):
        table.append([row(second)])
    return table


def parquet_count(home: Path) -> int:
    return len(glob.glob(f"{home}/**/*.parquet", recursive=True))


# --- what it removes ----------------------------------------------------------


@pytest.mark.trace("REQ-WP-038")
def test_rows_older_than_the_policy_go_and_the_rest_stay(catalog: Catalog) -> None:
    table = aged(catalog)

    apply(table, policy=RetentionPolicy(keep_ns=400 * SECOND), now_ns=NOW)

    assert sorted(table.read()["event_time_ns"].to_pylist()) == [700 * SECOND, 950 * SECOND]


@pytest.mark.trace("REQ-WP-038")
def test_the_pass_actually_frees_bytes(catalog: Catalog, tmp_path: Path) -> None:
    """The property the hand-rolled plane could not deliver, and the reason for
    [[ADR-060]].

    On that format every data file stayed referenced by the newest snapshot
    forever, so a pass ran, reported, verified clean and reclaimed nothing.
    """
    table = aged(catalog)
    before = parquet_count(tmp_path)

    report = apply(table, policy=RetentionPolicy(keep_ns=400 * SECOND), now_ns=NOW)

    assert report.files_removed > 0
    assert parquet_count(tmp_path) < before


@pytest.mark.trace("REQ-WP-038")
def test_a_pruned_table_still_reads_and_verifies(catalog: Catalog) -> None:
    table = aged(catalog)

    apply(table, policy=RetentionPolicy(keep_ns=400 * SECOND), now_ns=NOW)

    assert table.read().num_rows == 2
    assert verify(table).ok


@pytest.mark.trace("REQ-WP-038")
def test_running_twice_removes_nothing_more(catalog: Catalog) -> None:
    table = aged(catalog)
    policy = RetentionPolicy(keep_ns=400 * SECOND)

    apply(table, policy=policy, now_ns=NOW)
    again = apply(table, policy=policy, now_ns=NOW)

    assert again.files_removed == 0


# --- what it must not remove --------------------------------------------------


@pytest.mark.trace("REQ-WP-038")
def test_the_newest_snapshot_survives_any_policy(catalog: Catalog) -> None:
    """A table with no current state is not retained; it is deleted with extra
    steps."""
    table = aged(catalog)

    apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW)

    assert table.current() is not None
    assert verify(table).ok


@pytest.mark.trace("REQ-WP-038")
def test_a_pinned_snapshot_survives_and_still_reads(catalog: Catalog) -> None:
    """§6.4.9's Tier D: retained by experiment/model lineage policy.

    A snapshot an experiment names must survive however old it is. Expiring one
    destroys PRD §0 item 13's reproducibility in the quietest way available --
    the model still loads, the config still reads, and the run simply stops
    being checkable.
    """
    table = aged(catalog)

    apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW, pinned=(2,))

    assert 2 in table.snapshot_ids()
    assert table.read(snapshot_id=2).num_rows == 2


@pytest.mark.trace("REQ-WP-038")
def test_the_report_says_why_each_survivor_survived(catalog: Catalog) -> None:
    """ "Snapshot 2 is pinned" and "snapshot 5 is the newest" are the two facts
    somebody re-reading a pass needs, and a count tells them neither."""
    table = aged(catalog)

    report = apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW, pinned=(2,))

    assert any("pinned" in reason for reason in report.kept)
    assert any("newest" in reason for reason in report.kept)


@pytest.mark.trace("REQ-WP-038")
def test_a_pin_naming_a_snapshot_that_does_not_exist_is_refused(catalog: Catalog) -> None:
    """Likelier a typo than a wish, and honouring it silently prunes something
    somebody meant to keep -- the one outcome here that cannot be undone."""
    table = aged(catalog)

    with pytest.raises(NoSuchPin):
        apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW, pinned=(99,))


@pytest.mark.trace("REQ-WP-038")
def test_a_refused_pin_removes_nothing(catalog: Catalog, tmp_path: Path) -> None:
    """A refusal is not a half-run."""
    table = aged(catalog)
    before = parquet_count(tmp_path)

    with pytest.raises(NoSuchPin):
        apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW, pinned=(99,))

    assert parquet_count(tmp_path) == before
    assert table.read().num_rows == 4


# --- the durations are the caller's -------------------------------------------


@pytest.mark.trace("REQ-WP-038")
def test_the_policy_has_no_default_duration() -> None:
    """§6.4.9: "suggested semantics, not hard-coded durations". A default here
    would be a research default wearing a decision's clothes."""
    with pytest.raises(TypeError):
        RetentionPolicy()  # type: ignore[call-arg]


@pytest.mark.trace("REQ-WP-038")
def test_two_policies_over_one_table_keep_different_amounts(
    catalog: Catalog, tmp_path: Path
) -> None:
    generous = aged(catalog)
    apply(generous, policy=RetentionPolicy(keep_ns=900 * SECOND), now_ns=NOW)

    assert generous.read().num_rows == 3


@pytest.mark.trace("REQ-WP-038")
def test_the_report_names_the_cutoff_it_used(catalog: Catalog) -> None:
    table = aged(catalog)

    report = apply(table, policy=RetentionPolicy(keep_ns=400 * SECOND), now_ns=NOW)

    assert report.cutoff_ns == NOW - 400 * SECOND


# --- refusals rather than wrong answers ---------------------------------------


@pytest.mark.trace("REQ-WP-038")
def test_a_table_with_no_event_time_has_no_notion_of_old(catalog: Catalog) -> None:
    config = IcebergTable(
        name="market_config",
        schema=Schema(columns=(Column(name="key", type="string"),)),
        catalog=catalog,
    )
    config.append([{"key": "a"}])

    with pytest.raises(NoEventTime):
        apply(config, policy=RetentionPolicy(keep_ns=0), now_ns=NOW)


@pytest.mark.trace("REQ-WP-038")
def test_a_table_nobody_wrote_to_is_left_alone(catalog: Catalog) -> None:
    table = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)

    report = apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW)

    assert report.files_removed == 0
    assert report.snapshots_after == 0


# --- the capability rule ------------------------------------------------------


@pytest.mark.trace("REQ-WP-038")
def test_only_retention_deletes() -> None:
    """[[ADR-062]], asserted rather than assumed.

    [[ADR-059]] made this a type error: the table layer was handed a port with
    no `delete`. Iceberg's `FileIO` carries one beside the reads every table
    does, so the signature cannot hold the line any more. This is weaker, and it
    is what there is -- the same shape as the import checks `test_isolation.py`
    runs for PRD §29.0's layering rule.
    """
    import channelflow

    root = Path(channelflow.__file__).parent
    offenders = [
        path.relative_to(root)
        for path in root.rglob("*.py")
        if path.name != "retention.py" and "io.delete(" in path.read_text()
    ]

    assert offenders == [], f"only retention.py may delete an object: {offenders}"


@pytest.mark.trace("REQ-WP-038")
def test_the_rule_guards_the_irreversible_step_and_not_the_other_one() -> None:
    """`table.delete(row_filter)` is not what the rule is about, and the first
    version of the check could not tell the two apart.

    A row delete is a commit: the rows leave the current snapshot and every
    earlier snapshot still holds them, so it is undone by reading one. An object
    delete is not undone by anything. The rule guards the second, which is why
    `delete_rows_before` may live on the table and `io.delete` may not.
    """
    from channelflow.lakehouse import iceberg

    source = Path(iceberg.__file__).read_text()

    assert "table.delete(" in source, "the row delete lives on the table"
    assert "io.delete(" not in source, "the object delete does not"


@pytest.mark.trace("REQ-WP-038")
def test_a_surviving_snapshot_keeps_its_name(catalog: Catalog) -> None:
    """The finding that nearly made retention quietly destroy reproducibility.

    Snapshot ids were positions in a list. Expiring a snapshot renumbers
    positions, so a run that recorded "snapshot 3" would resolve to a *different
    dataset* after a retention pass, with nothing to say so -- and PRD §0 item
    13's reproducibility claim would have become untrue in the one operation
    least likely to be re-read.

    They are Iceberg's sequence numbers now, which survive expiry. A pinned
    snapshot answers to the same name afterwards as before, which is the only
    thing that makes pinning mean anything.
    """
    table = aged(catalog)
    named = table.snapshot_ids()[1]
    rows_then = table.read(snapshot_id=named).to_pylist()

    apply(table, policy=RetentionPolicy(keep_ns=0), now_ns=NOW, pinned=(named,))

    assert named in table.snapshot_ids()
    assert table.read(snapshot_id=named).to_pylist() == rows_then


@pytest.mark.trace("REQ-WP-038")
def test_a_table_that_can_never_be_pruned_says_so_before_it_says_anything_else(
    catalog: Catalog,
) -> None:
    """Two refusals apply at once, and which one speaks is a decision.

    A table with no event time has no notion of old, so no policy can ever
    prune it; a bad pin is a mistake in one call. The first is the more
    fundamental answer and it wins, because telling somebody their pin is wrong
    invites them to fix the pin and try again on a table that will never be
    prunable.
    """
    config = IcebergTable(
        name="market_config",
        schema=Schema(columns=(Column(name="key", type="string"),)),
        catalog=catalog,
    )
    config.append([{"key": "a"}])

    with pytest.raises(NoEventTime):
        apply(config, policy=RetentionPolicy(keep_ns=0), now_ns=NOW, pinned=(99,))
