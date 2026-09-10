# Implementation Plan: The experiments adopt the reporting gate

**Branch**: `bias-011-experiment-adoption` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/057-experiment-gate-adoption/spec.md`

## Summary

Make [[REQ-REPRO-001]]'s gate reachable from all eighteen research entry points,
and make "all of them" a fact the suite checks.

The approach in one sentence: **a comparison learns to name its field, and one
seam turns a named field into registry rows.** Nothing about the gate changes,
and nothing about what any experiment computes changes.

The load-bearing choice is where the field comes from. The variants are the
research modules' own objects — `RollingOLSChannel(bands="std")`,
`AblationArm(name="channel_only", ...)` — and every one of them is a frozen
dataclass, so a variant's configuration is `dataclasses.asdict` of the object
that produced it. Verified before planning: `config_hash` accepts what comes out
(including `None` and nested tuples), and the two `RollingOLSChannel` variants
that differ only in `bands` hash differently. That last check is the whole
argument against the cheaper design — hashing the variant's *name* would have
collided those two and put indistinguishable rows in the registry while looking
like full coverage.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new. `channelflow.experiments` (registry, gate, `config_hash`) and `channelflow.research` as they stand.

**Storage**: the canonical plane, through the existing `Registry`. No schema change.

**Testing**: pytest, with `@pytest.mark.trace("REQ-BIAS-011")` markers; a mutation sweep over the seam.

**Target Platform**: library, no service.

**Project Type**: single project.

**Performance Goals**: none. The seam runs once per reported experiment.

**Constraints**: a research function stays pure over its inputs — no store, no git, no clock (REQ-REPRO-001's FR-013). The seam is the only thing that touches the registry.

**Scale/Scope**: 18 entry points, 17 distinct comparison types, 11 of which take an injected field.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing | Verdict |
|---|---|---|
| **XI. Results are reproducible** | This feature exists to make the four hashes reach a research result. A variant's config hash must distinguish variants that differed. | **Pass, and it is the point.** FR-003/SC-003 are exactly this gate. |
| **XIV. Everything is traceable** | Adoption is worthless if it is a snapshot. | **Pass.** FR-012's discovered check is what keeps it true past today. |
| **XII. Correctness precedes performance** | The seam re-reads the registry to avoid double-writing. | **Pass.** A full read per report is right at these sizes and named in research.md. |
| **XIII. Work is incremental** | Eighteen modules in one change is not small. | **Pass, under protest recorded.** ADR-054 already refused a subset; a staged adoption leaves the requirement at `specified` either way, so staging buys nothing but a longer red window. |
| **I. No look-ahead** | Untouched: nothing here reads market data. | Not applicable. |
| **III. History is immutable** | The registry is append-only; reporting twice must not double it. | **Pass.** FR-010, via the run-hash watermark ([[ADR-056]]). |

No violations. Complexity Tracking is therefore empty and removed.

## Project Structure

### Documentation (this feature)

```text
specs/057-experiment-gate-adoption/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
└── checklists/
```

### Source Code (repository root)

```text
src/channelflow/experiments/
├── fields.py            # NEW: Field, Compared, config_of, report_comparison
└── __init__.py          # exports the four

src/channelflow/research/
├── <18 modules>         # each declares EXPERIMENT and COMPARISON,
│                        # and its comparison grows a `field` property
└── __init__.py

tests/unit/experiments/
└── test_fields.py       # NEW: the seam's own behaviour

tests/unit/research/
└── test_gate_adoption.py # NEW: the discovered check over the package
```

**Structure Decision**: single project, existing directories. The seam lives in
`channelflow.experiments` rather than `channelflow.research` because it belongs
to the gate, not to any experiment.

Neither package imports the other today — checked, not assumed. This feature
creates the edge, and its direction is the decision: `research` will import
`experiments`. That way the mechanism stays ignorant of every experiment, which
is what lets a nineteenth arrive without touching it. The opposite edge would
make the gate import all eighteen comparison types to know about them, which is
both a cycle waiting to happen and the design FR-012 exists to avoid.
