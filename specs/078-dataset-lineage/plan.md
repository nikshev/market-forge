# Implementation Plan: A registration names the dataset it was trained on

**Branch**: `wp-040-dataset-lineage` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

## Summary

One value object, `DatasetOrigin`, carried from where a dataset is read to where
a model is registered, plus a resolver and a pin source for retention.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: the registry's existing suite plus new cases; a retention test that
takes its pins from a registry; a mutation sweep.

**Constraints**: no default on the new field ([[ADR-015]]); identity by content
hash ([[ADR-053]]).

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **XI. Reproducible results** | The missing quarter of PRD §0 item 13. | **Pass**, and it is the feature. |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-040`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/models/registry.py        # + DatasetOrigin, + the field, + pins_for
src/channelflow/dataset/certified.py      # + the origin a study passes through
src/channelflow/pipeline/study.py         # threads it into each Registration
tests/unit/models/test_registry.py        # + the new cases
tests/unit/lakehouse/test_retention.py    # + pins read from a registry
```

## Where the origin comes from

Whoever read the table knows which snapshot they read. `DatasetOrigin.of(table,
snapshot_id)` takes it from the table itself, so the content hash is the one the
plane computed rather than one the caller typed.

It is **supplied, not inferred**, at every step after that. A layer that
re-derived it would ask the table what it holds *now*, which is the right answer
to a different question and is wrong exactly when a table has moved on — which
is the case the citation exists for.

## Three outcomes, not two

`resolve(origin, table)` answers:

| | Meaning |
|---|---|
| `RESOLVED` | the snapshot is there and its content hash matches |
| `CHANGED` | the snapshot is there and holds something else |
| `GONE` | the snapshot is not there |

A check that only asked "does the id resolve" would pass `CHANGED`, which is the
case a citation is supposed to catch: an id is a name and a hash is a claim
about what was under it.

`GONE` is not an error. A registration whose dataset has been expired is still a
record of a run that happened, and refusing to read it would make every report
unreadable after a legitimate retention pass.

## Closing retention's loop

`pins_for(registry, table)` returns the snapshots registrations name for that
table. Retention takes them instead of being handed a list by hand, which is
what [[REQ-WP-038]] left open and the reason this requirement exists.

An empty result is an empty tuple, and the caller can tell it from not having
asked — a distinction worth keeping, because "no lineage to protect" and "I
forgot to look" produce the same prune.
