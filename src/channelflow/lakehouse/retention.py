"""PRD section 6.4.9's retention tiers, on the canonical plane.

# @trace: REQ-WP-038

Section 6.4.9 asks for retention "configurable per event family" and says, in
the same breath, "suggested semantics, **not hard-coded durations**". The
section declines to name a number; so does this. Every duration is an argument,
and the operator choosing one is choosing what their system forgets.

**This is the only thing in the system that destroys.** Everything else appends,
so the ways it can go wrong are not the ways the rest of the code can go wrong,
and the worst of them leaves a table that reads perfectly and cannot answer a
question it could answer yesterday.

Three of them are guarded here:

- **Tier D.** "Retained by experiment/model lineage policy": a snapshot an
  experiment names survives however old it is. Expiring one destroys section 0
  item 13's reproducibility in the quietest way available -- the model still
  loads, the config still reads, and the run simply stops being checkable.
- **The newest snapshot always survives**, whatever the policy says. A table
  with no current state is not retained; it is deleted with extra steps.
- **A pin nobody can honour is refused.** It is likelier a typo than a wish, and
  honouring it silently prunes something somebody meant to keep -- the one
  outcome here that cannot be undone.

The pass is three operations, and only the last frees bytes: delete the rows
that aged out, expire the snapshots that still point at the old files, remove
what nothing references any more. Iceberg supplies the first two; the third is
this module's, and [[ADR-062]] makes it the only place that deletes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from channelflow.lakehouse.iceberg import IcebergTable, NoEventTime


class NoSuchPin(LookupError):
    """A pin naming a snapshot the table does not have."""


@dataclass(frozen=True)
class RetentionPolicy:
    """How much event-time history is worth keeping.

    No default. PRD section 6.4.9 declines to name a duration, and a number
    written here would be a research default wearing a decision's clothes
    (section 13.11).
    """

    keep_ns: int


@dataclass(frozen=True)
class RetentionReport:
    """What a pass did, and what it refused to do.

    `kept` carries reasons rather than counts: "snapshot 2 is pinned" and
    "snapshot 5 is the newest" are the two facts somebody re-reading a pass
    needs, and a number tells them neither.
    """

    table: str
    cutoff_ns: int
    snapshots_before: int
    snapshots_after: int
    files_removed: int
    kept: tuple[str, ...]


def apply(
    table: IcebergTable,
    *,
    policy: RetentionPolicy,
    now_ns: int,
    pinned: Sequence[int] = (),
) -> RetentionReport:
    """Age out what the policy says, keeping what something still depends on.

    `now_ns` is an argument, as every instant in this system is: a clock reading
    would make a replay expire different data from the run it replays.
    """
    if table.schema.event_time_column is None:
        raise NoEventTime(
            f"{table.name} declares no event-time column, so it has no notion of "
            "rows being old enough to drop"
        )

    before = table.snapshot_ids()
    unknown = [pin for pin in pinned if pin not in before]
    if unknown:
        # Refused before anything is touched: a refusal is not a half-run.
        raise NoSuchPin(
            f"{table.name} has snapshots {before or 'none'}, so {unknown} cannot be "
            "pinned; a pin nobody can honour is likelier a typo than a wish"
        )

    cutoff_ns = now_ns - policy.keep_ns
    if not before:
        return RetentionReport(
            table=table.name,
            cutoff_ns=cutoff_ns,
            snapshots_before=0,
            snapshots_after=0,
            files_removed=0,
            kept=(),
        )

    table.delete_rows_before(cutoff_ns)

    after_delete = table.snapshot_ids()
    newest = after_delete[-1]
    keep = sorted({*pinned, newest})
    table.expire_snapshots_except(keep)

    # The only deletion in the system ([[ADR-062]]). It lives here rather than
    # on the table because the table is handed to everything and this is not.
    handle = table.handle()
    orphans = table.unreferenced_files() if handle is not None else ()
    for path in orphans:
        handle.io.delete(path)  # type: ignore[union-attr]
    removed = len(orphans)

    return RetentionReport(
        table=table.name,
        cutoff_ns=cutoff_ns,
        snapshots_before=len(before),
        snapshots_after=len(table.snapshot_ids()),
        files_removed=removed,
        kept=tuple(
            f"snapshot {snapshot_id} is {'pinned' if snapshot_id in set(pinned) else 'the newest'}"
            for snapshot_id in keep
        ),
    )
