# Implementation Plan: The API's reads from the canonical plane

**Branch**: `store-002-lakehouse-repository` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Four table modules, one repository, and one conformance suite that runs every
behaviour against both implementations.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.lakehouse`, the domain packages it maps.

**Testing**: 31 conformance tests over two implementations, 7 mapping tests, and
every existing endpoint test parametrised over both — 138 in the two packages.

**Target Platform**: `src/channelflow/tables/`, `src/channelflow/api/`.

**Constraints**: FR-002 and FR-003 (one suite, both implementations), FR-008
(the score join).

**Scale/Scope**: 4 modules, 1 repository, 17 mutations.

## Constitution Check

- **I (no look-ahead, ever)** — a channel snapshot is never later than the
  instant asked for, enforced by the plane's point-in-time read and again by the
  reader.
- **VII (live and replay are the same code)** — one port, two implementations,
  one suite. That is the principle applied to storage.
- **XIV** — traces to REQ-STORE-002.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/tables/rows.py         # NEW: reading one value, or refusing
src/channelflow/tables/channels.py     # NEW: §29.6
src/channelflow/tables/signals.py      # NEW: §29.7 core + transitions
src/channelflow/tables/features.py     # NEW: §29.5 long form, markets, scores
src/channelflow/api/lakehouse_repository.py   # NEW
```

**Structure Decision**: the plane gained three container types — `float_list`,
`string_list`, `float_map` — rather than growing six child tables. §29.6 asks a
channel snapshot for "forecast arrays" and "quality components" by name; Arrow
and Parquet carry both natively and DuckDB and Trino query them, which is the
whole reason the physical format was chosen. A transition history stays a child
table, because §29.7 asks for a core plus a separate table and because four
parallel lists only mean anything read together.

## Approach

**One suite, both implementations.** Two suites would drift, and the first
divergence would be a behaviour one has and the other does not with nothing
saying which is right. Every existing endpoint test is parametrised too, so
[[ADR-019]]'s promise is something the suite fails on.

**A score has its own id.** Contributions joined on the instant give a score
every group any score at that instant had — and scores tie on their instant
whenever the caller does not supply one. The id is content-derived, so the same
score written twice is the same score and a re-run of a backfill does not look
like new data.

**A transition history is restored by an ordinal.** Two transitions can share a
bar close time — a touch and a rejection inside one bar — so a close time is not
an order.

**There is no `cap` column on a contribution.** A group's cap is a §22.1
constant reached through `GROUP_CAPS`, not a property of one contribution, and
storing it would create a second source of truth a reader could believe over the
constant.

## Complexity Tracking

> No violations.
