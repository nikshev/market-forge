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

## PLANNING STOPPED: this frees no bytes, and that is not a detail

`Table.append` writes `files=(*parent.files, file)`. Manifests are strictly
cumulative, so **the newest snapshot names every data file ever written to the
table.** The newest snapshot always survives — a table with no current state is
not retained, it is deleted with extra steps — therefore no data file is ever
unreferenced, therefore snapshot expiry removes **manifests only**, which are
small JSON documents.

A pass built to this plan would run, report, verify clean, and reclaim
essentially nothing. It would be a retention feature in the sense that matters
least: correct, tested, and not retention.

Delivering PRD §45's "S3 cold retention" needs a second operation this plan does
not contain — **compaction**: commit a new snapshot naming only the files worth
keeping, expire the older manifests, then remove what nothing references any
more. That is a materially larger and more dangerous feature, because it is the
first thing in this system that deletes market data, and it decides that
point-in-time reads before the cutoff stop working. Whether that trade is
acceptable is a decision about the trading system, not about the code.

Planning stops here and the requirement stays `specified`. [[ADR-059]] stands on
its own either way: whichever shape retention takes, the ability to delete
belongs to it and not to the commit path.
