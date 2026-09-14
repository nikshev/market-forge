"""One pass over a table: prune, compact, retain.

# @trace: REQ-WP-070

Three operations that each fix something the others do not, and whose order is
not interchangeable.

**Metadata pruning first**, because it is a property rather than a rewrite: it
changes what the commits below it leave behind, and setting it afterwards would
let this pass write files it then has to collect.

**Compaction second.** It rewrites the live rows into one file, which is what
[[REQ-WP-068]] measured taking a read from 6478ms to 45ms -- and it *unreferences*
every file it replaced without removing one.

**Retention last**, because that is what removes them. Reversed, it finds
nothing unreferenced and compaction's output waits a whole cycle to be
collected.

None of the three is optional. Measured on a deployment before any of them: 2.6
MB of bar data against 304.9 MB of metadata and 933 data files for a table whose
current snapshot used one.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass

from channelflow.lakehouse.iceberg import IcebergTable
from channelflow.lakehouse.retention import RetentionPolicy, RetentionReport
from channelflow.lakehouse.retention import apply as apply_retention


@dataclass(frozen=True)
class MaintenanceReport:
    """What one pass did to one table, in the order it did it."""

    table: str
    metadata_pruned: bool
    files_before: int
    retention: RetentionReport | None
    seconds: float

    @property
    def line(self) -> str:
        parts = [f"{self.table}:"]
        parts.append(
            "metadata pruning set" if self.metadata_pruned else "metadata pruning already set"
        )
        parts.append(
            f"{self.files_before} file(s) compacted"
            if self.files_before > 1
            else "nothing to compact"
        )
        if self.retention is not None:
            parts.append(
                f"{self.retention.snapshots_before} -> "
                f"{self.retention.snapshots_after} snapshot(s), "
                f"{self.retention.files_removed} file(s) removed"
            )
        return " ".join(parts) + f" in {self.seconds:.1f}s"


def run(
    table: IcebergTable,
    *,
    policy: RetentionPolicy | None = None,
    now_ns: int | None = None,
    pinned: Sequence[int] = (),
) -> MaintenanceReport:
    """One pass. `policy` of `None` compacts without expiring anything.

    Retention is optional because it is the one operation that destroys, and an
    operator who wants a faster read is not necessarily asking to forget
    anything. Compaction alone leaves the old files in place, which is safe and
    costs storage -- stated, so the choice is visible.
    """
    started = time.perf_counter()
    pruned = table.prune_metadata()
    before = table.compact()
    report = None
    if policy is not None:
        report = apply_retention(
            table,
            policy=policy,
            now_ns=now_ns if now_ns is not None else time.time_ns(),
            pinned=pinned,
        )
    return MaintenanceReport(
        table=table.name,
        metadata_pruned=pruned,
        files_before=before,
        retention=report,
        seconds=time.perf_counter() - started,
    )
