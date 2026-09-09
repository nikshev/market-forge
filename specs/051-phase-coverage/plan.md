# Implementation Plan: Phase coverage and the last derived acceptance criteria

**Branch**: `phase-coverage` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Criteria derived for the last three phases, two coverage lists added to all
eleven phase notes, and one test module that reads both lists and fails when
either is wrong.

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: `tools.trace.frontmatter`.

**Testing**: pytest, over the real vault rather than a fixture — the point is
the notes that exist, not a note a fixture builds.

**Target Platform**: `vault/10-requirements/`, `tests/tools/trace/`.

**Constraints**: FR-005 and FR-006 (the two checks), FR-003 (the marker scan).

**Scale/Scope**: 11 notes, 1 derivation document, 13 tests.

## Constitution Check

- **XIV (traceability)** — this is the rule's own subject: a phase's claim about
  what delivers it becomes checkable rather than asserted.
- **XI (results are reproducible)** — the tests read the vault, so they say what
  is true today rather than what was true when they were written.

**Gate result: PASS.**

## Project Structure

```text
vault/10-requirements/REQ-PHASE-*.md            # + criteria, covers, not_delivered
docs/superpowers/specs/2026-09-09-phase-acceptance-design.md   # NEW
tests/tools/trace/test_phase_coverage.py        # NEW
```

**Structure Decision**: the lists live in frontmatter and are checked by a test
rather than by a validator rule. `collect_requirements` ignores unknown keys, so
a seventh rule would mean changing the collector, the model and the validator
for a relationship only the phase notes have. That is the same arrangement
`hard_gated` had before R5 existed, and `test_vault_hard_gated.py` is the
precedent.

## Approach

**Every phase is `planned`, and that is the finding.** Every one of the eleven
has at least one deliverable nothing in this repository provides — a virtual
clock in Phase 0, chart markers in Phase 1A, a model registry in Phase 7, the
whole of Phase 8. Setting them all to `implemented` would have been one edit and
a lie the notes themselves contradict.

**The gap lists are specific.** "UI panes for the book features: the web app has
no order-book or order-flow pane" is checkable by a reader in a minute. "UI
incomplete" is not.

**The marker is not retired.** Re-run the extractor over a PRD section with no
acceptance criteria and it comes back, meaning exactly what it meant before. The
scan is what makes that loud.

## Complexity Tracking

> No violations.
