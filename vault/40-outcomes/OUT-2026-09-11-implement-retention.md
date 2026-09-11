---
id: OUT-2026-09-11-implement-retention
step: implement
records: [REQ-WP-038]
commit: null
---

## What was done

`lakehouse/retention.py`: delete what aged out, expire the snapshots that still
point at the old files, remove what nothing references. 17 tests, every gate
green, and the pass measurably frees bytes — which is the thing the hand-rolled
plane could not do and the whole reason for [[ADR-060]].

[[REQ-WP-038]] reaches `implemented`. [[REQ-PHASE-8]] loses a fourth
deliverable.

## The two defects the sweep found, and they were in the code

**A read returned rows a delete had removed.** `_in_commit_order` reconstructed
the order by walking the snapshot chain and taking every file any snapshot
named. A file a delete drops is still named by every earlier snapshot, so the
read went on returning rows the table no longer held. Retention's own tests
passed anyway, because the expiry that follows the delete removed the snapshots
that were carrying the stale files — the feature masked the defect that would
have made it useless.

**Snapshot ids were positions, and expiry renumbers positions.** A run that
recorded "snapshot 3" would have resolved to a *different dataset* after a
retention pass, with nothing to say so. That is PRD §0 item 13's reproducibility
claim becoming untrue in the one operation least likely to be re-read, and it is
the exact failure Tier D's pinning exists to prevent — the pin would have
survived and pointed somewhere else.

Ids are Iceberg's sequence numbers now. Measured: expiring the first two
snapshots of four leaves the survivors named 3 and 4. A fresh table still counts
from one, so nothing above noticed.

Both were found by one mutant — "the pin check runs after the damage" — which
survived for neither of the reasons I guessed. Chasing why it survived is what
turned up both.

## And a third, found by the fix

With ids stable, a pinned snapshot survived by name and **read back in a
different order than it was written**. Commit order had been reconstructed by
first appearance across the chain, and expiry removes the links that carried
that information. The order now comes from the sequence number Iceberg records
against each data file, which survives expiry — and which also costs one scan
instead of one per snapshot.

## What [[ADR-062]] had to be told apart

The capability rule first matched `.delete(` anywhere in the source, and caught
`table.delete(row_filter)` — which is a **commit**: the rows leave the current
snapshot, every earlier snapshot still holds them, and reading one undoes it.
`io.delete(path)` is undone by nothing. The crude check would have pushed the
recoverable operation out of the table layer while leaving the unrecoverable one
unremarked. The rule guards the irreversible step, and the ADR now says so.

## What is still open

- **Nothing produces the pinned set.** `Registration` still does not record
  which dataset snapshot a model trained on — the finding this requirement's
  extraction produced, and still its own work.
- **Nothing schedules a pass.**
- **Tiers A and C have no store**, which is not deferred work hiding here.
