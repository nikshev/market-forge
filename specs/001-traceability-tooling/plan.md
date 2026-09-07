# Implementation Plan: Deterministic Traceability Graph and Coverage Validator

**Branch**: `001-traceability-tooling` | **Date**: 2026-09-07 | **Spec**: `specs/001-traceability-tooling/spec.md`

**Input**: Feature specification from `specs/001-traceability-tooling/spec.md`

**Note**: Written retroactively against the already-built `tools/trace/`
package (Tasks 4-10 of the SDD-traceability-infra plan). It records the
approach that was actually taken, and the alternatives rejected, rather than
proposing a new design.

## Summary

Build one collector per artifact kind (requirements, specs, tests, source,
outcomes, decisions), assemble them into a single in-memory `TraceGraph`,
run seven stateless coverage rules over it, and render two kinds of output —
a machine-readable JSON dump and human-readable Markdown (a dashboard plus
per-requirement `## Trace` sections) — using a strict marker-pair rewrite
that never touches text it doesn't own.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `networkx` (cycle detection, JSON/Mermaid export),
`pytest` (test collection is itself a data source, via a first-party plugin)

**Storage**: Flat files — Markdown notes under `vault/`, `spec.md` under
`specs/<NNN-slug>/`, a JSON dump under `.trace/`. No database.

**Testing**: `pytest`, including `pytester` for exercising the pytest plugin
in an isolated sub-run.

**Target Platform**: Local developer machine / CI, run via `make`.

**Project Type**: CLI + library (`tools/trace/`), consumed by a Makefile and
a pre-commit hook.

**Performance Goals**: Not perf-sensitive; graph size is bounded by the
number of requirements, specs, tests and source files in one repository
(currently ~90 nodes). No goal beyond "instant enough for a pre-commit hook."

**Constraints**: Every edge must be explicit and machine-checkable — no
fuzzy matching, no LLM-derived link, ever (this is the requirement's central
constraint, not an implementation detail).

**Scale/Scope**: One repository's worth of requirements, specs, tests and
source; not designed to span multiple repositories.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Principle XIV ("Everything is traceable") is the constitution principle this
feature exists to satisfy, and is also the gate: a graph and validator that
depended on fuzzy matching, or that could be bypassed by a status edit alone,
would fail it by construction. No other principle (I-XIII) constrains this
feature — they govern market-data and trading code, which this feature does
not touch. Gate: **PASS**.

## Project Structure

### Documentation (this feature)

```text
specs/001-traceability-tooling/
├── plan.md              # This file
├── tasks.md             # Phase 2 output
└── spec.md              # Phase 0 output (already written)
```

No `research.md`, `data-model.md`, `contracts/` or `quickstart.md` were
needed: there was no unresolved technical unknown to research (the approach
was already implemented and observed working), no external contract surface
(the "contract" is the marker-pair and frontmatter-field conventions
documented directly in the spec and in `CLAUDE.md`), and no data model beyond
the three dataclasses in `tools/trace/model.py`, which the spec's Key
Entities section already covers.

### Source Code (repository root)

```text
tools/trace/
├── model.py            # Node, Edge, TraceGraph, Status
├── frontmatter.py       # YAML frontmatter / body split
├── collect.py           # One collector function per artifact kind
├── graph.py              # build_graph(), JSON/Mermaid/networkx export
├── validate.py           # R1-R7 over a TraceGraph
├── dashboard.py          # marker-pair rewrite, dashboard + per-note Trace
├── cli.py                # build / validate / dashboard / show
└── pytest_plugin.py       # --trace-dump collection hook

tests/tools/trace/
└── test_*.py             # one test module per tools/trace/*.py module
```

**Structure Decision**: Single project, matching the rest of the repository's
`tools/<package>/` + `tests/tools/<package>/` convention. No `src/` layout was
introduced for this feature since it is tooling, not product code.

## Complexity Tracking

No Constitution Check violations. Table intentionally empty.
