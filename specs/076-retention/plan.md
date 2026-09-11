# Implementation Plan: Retention expires by policy

**Branch**: `wp-038-retention` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

## Summary

`lakehouse/retention.py`: a policy, a pass, and a report.

The pass decides which snapshots survive — by age, by pin, and by the rule that
the newest always does — then removes each expired manifest before the files
that no surviving manifest still names.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: unit tests on the in-memory store, an integration test on MinIO,
and a mutation sweep. A pruned table is verified with [[REQ-WP-037]]'s `verify`,
unchanged.

**Constraints**: no duration in the code; no clock — "now" is an argument, as
every instant in this system is.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **V. Append-only** | The one operation that destroys, confined to a module the commit path cannot reach. | **Pass**, via [[ADR-059]]. |
| **X. Parameters are arguments** | §6.4.9 declines to name durations, so this does too. | **Pass.** |
| **XI. Reproducible results** | A pinned snapshot outlives any policy. | **Pass**, and it is the feature. |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-038`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/lakehouse/store.py           # + PrunableObjectStore, + delete on both stores
src/channelflow/lakehouse/retention.py       # NEW
src/channelflow/lakehouse/__init__.py        # + exports
tests/unit/lakehouse/test_retention.py       # NEW
tests/integration/test_retention_on_minio.py # NEW
vault/20-decisions/ADR-059.md                # the capability decision
```

## Which snapshot is "old"?

A snapshot's age is measured by its **latest event time**, not by when it was
committed — nothing here records a commit time, and a clock reading would make a
replay expire different snapshots from the run it replays.

`Snapshot` already carries `event_time_max_ns` for exactly this kind of
question. A snapshot with no event time — a table with no event-time column —
cannot be aged and is therefore kept, which is the conservative answer and the
only honest one.

## Removing in the inverse order

Writing is data, then manifest. Removal is manifest, then data:

1. delete the expired manifests, newest expired first;
2. compute the set of files no *surviving* manifest names;
3. delete those.

After step 1 the expired snapshots are gone from `snapshot_ids` and every
surviving manifest is still fully backed. An interruption anywhere in step 3
removes only files nothing names. There is no window in which a surviving
manifest points at an absent file, which is what makes an interrupted pass safe
rather than merely unlikely to be interrupted.

## The stop, and why it is over

Planning stopped here on the hand-rolled plane: expiry freed nothing, because no
operation that plane offered could make a data file unreferenced. [[ADR-060]]
replaced it and [[REQ-WP-039]] landed the replacement, and Iceberg has the
missing operation. `IcebergTable` already carries the three steps:
`delete_rows_before`, `expire_snapshots_before`, `unreferenced_files`.

The stop also flagged a second thing as a decision for whoever owns the trading
system: retention makes point-in-time reads before the cutoff stop working. On
reflection that is not an open decision, and saying why matters more than the
conclusion.

PRD §6.4.9 asks for retention tiers in as many words, so *that data ages out* is
already decided by the document this repository implements. What §6.4.9 pointedly
declines to decide is **how long** — "suggested semantics, not hard-coded
durations" — and that is the part this feature must not decide either. Every
duration is an argument, and the operator choosing one is choosing what their
system forgets.

So the mechanism is buildable now and the judgement stays with the caller, which
is where the requirement put it.

## What the pass does

1. **Refuse a pin nobody can honour.** A pin naming an absent snapshot is more
   likely a typo than a wish, and honouring it silently prunes something
   somebody meant to keep — the one outcome here that cannot be undone.
2. **Delete the rows that aged out**, by event time, against the cutoff the
   caller's policy names.
3. **Expire the snapshots that still point at the old files**, keeping every
   pinned one and always the newest.
4. **Remove what nothing references any more**, and only that.

Steps 2 and 3 are Iceberg's. Step 4 is ours.

## The capability, after the migration

[[ADR-059]] gave deletion to a `PrunableObjectStore` the table layer could not
be handed. That port is gone: the plane is Iceberg, and Iceberg's own `FileIO`
carries `delete` alongside the reads every table does.

The type-level guarantee does not survive, and pretending otherwise would be
worse than losing it. What replaces it is an asserted one: a test reads the
source and fails if any module other than `retention.py` calls `delete` on a
`FileIO`. That is weaker than a signature and stronger than a convention, and it
is the same shape as the import check `test_isolation.py` already runs.
