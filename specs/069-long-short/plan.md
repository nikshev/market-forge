# Implementation Plan: Long/short positioning, and its absence

**Branch**: `wp-031-long-short` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Two optional fields on `DerivativesState`, four readings over them, three
registry entries — and every one of those pieces exists to keep one distinction
alive: an absent ratio is not a balanced book.

The fields are the deliverable. The work is in the two places the distinction
can quietly die: a default that turns silence into 1.0, and a z-score history
that counts silent states as observations. Both are cheap to write correctly and
impossible to notice when written wrongly, because both produce numbers.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: 16 unit tests in `tests/unit/derivatives/test_positioning.py`, the
existing derivatives suites unchanged, the golden `DerivativesState` fixture
regenerated and its diff reviewed, and a seven-mutant sweep over the new module.

**Constraints**: the z-score is [[ADR-026]]'s — reused, not reimplemented. The
staleness rule is REQ-WP-026's, applied to the reading rather than to the state
that carried it.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **I. No look-ahead, ever** | The z-score history is built from states at or before the instant asked about. | **Pass**, asserted by a window only future readings could fill. |
| **VI. Every feature is documented** | Three registry entries, each stating what absence means. | **Pass.** |
| **XIII. Work is incremental** | Carrying and reading positioning; the connector mapping that fills it is the derivatives path's. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-031` in the module, `@pytest.mark.trace` on all 16 tests. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/domain/derivatives.py            # + two optional ratios, gt=0.0
src/channelflow/derivatives/positioning.py       # NEW: four readings
src/channelflow/derivatives/__init__.py          # + the four exports
src/channelflow/features/derivatives.py          # + three registrations
tests/unit/derivatives/test_positioning.py       # NEW: 16 tests
tests/fixtures/domain/derivatives_state.json     # regenerated: two null keys
```

**Structure Decision**: positioning is its own module rather than more functions
in `state.py`. `state.py` holds the machinery every derivative reading shares —
`state_at`, `require_fresh`, `z_score`. Positioning is a consumer of that
machinery, and the split keeps the shared floor from growing a per-feature wing
each time a feature lands.
