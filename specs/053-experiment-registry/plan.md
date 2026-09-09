# Implementation Plan: Run identity, registry and reporting gate

**Branch**: `repro-001-experiment-registry` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `channelflow.experiments`: the four-component run identity,
canonical hashing for the two components that are not already hashes, the
registry as a lakehouse table, and the gate between a run and a reportable
result.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.lakehouse`. No new third-party packages.

**Testing**: 43 unit tests. No integration test: the registry is a lakehouse
table, and the lakehouse's own MinIO tests already cover the storage path.

**Target Platform**: `src/channelflow/experiments/`.

**Constraints**: FR-011 and FR-012 (both gates), FR-013 (no clock, no git).

**Scale/Scope**: 4 modules, 43 tests, 27 mutations.

## Constitution Check

- **XI (results are reproducible)** — this is that principle made into a
  refusal rather than an aspiration.
- **V (finalized records are not rewritten)** — the registry inherits it from
  the lakehouse; a registry that could be tidied up would defeat rule 11.
- **XIV** — traces to REQ-REPRO-001 and REQ-BIAS-011.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/experiments/identity.py   # the four components
src/channelflow/experiments/hashing.py    # config and dataset composition
src/channelflow/experiments/registry.py   # the table on the canonical plane
src/channelflow/experiments/report.py     # the gate
```

**Structure Decision**: the registry is a lakehouse table rather than a
PostgreSQL one. PRD §29.B lists `backtest_runs` and `experiment_membership`
among the Iceberg tables and [[ADR-002]] made object storage canonical; a
registry that could be edited after the fact would defeat the rule it enforces.

## Approach

**Absence is stated, never blank.** Three failure modes look identical in a
record of four strings: a run that fits no model, a run whose artifact nobody
wrote down, and a commit taken from a dirty tree. The first is fine. The other
two are the ones that happen by accident, the third especially — `git rev-parse
HEAD` answers cheerfully in a dirty tree.

**Storage is not enforcement** ([[ADR-054]]). Rule 11 becomes checkable when
reporting a winner requires naming the field it won, and every name in that
field has to be on record. That is the honest limit and the code says so: it
cannot stop someone who never mentions a variant.

**Config hashing is length-prefixed and type-tagged**, like the lakehouse's row
encoding and for the same reasons — but it is not the same function, because
that one encodes a flat row against a declared schema and this one encodes an
arbitrary nested structure with none.

## Complexity Tracking

> No violations.
