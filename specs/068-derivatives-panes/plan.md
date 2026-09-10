# Implementation Plan: Lower panes for the derivatives features

**Branch**: `wp-030-derivatives-panes` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Four entries in `PANES`, and a Python test that reads that list from the file
and compares it against the feature registry.

The four entries are the deliverable; the test is the work. A pane naming a
feature nobody registers renders "no readings of this feature" forever, and the
list will grow to nine and beyond, edited by people not looking at the registry.

## Technical Context

**Language**: TypeScript 5 and Python 3.12 · **Dependencies**: none new

**Testing**: the cross-language check plus the existing pane suites; a mutation sweep over both halves.

**Constraints**: the check reads the real list, and refuses a source it cannot parse.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VI. Every feature is documented** | Every pane names a registered feature, mechanically. | **Pass**, and that is the feature. |
| **XIII. Work is incremental** | DEX panes wait for Phase 4's data. | **Pass.** |
| **XIV. Everything is traceable** | The check is the trace between two lists. | **Pass.** |

No violations.

## Project Structure

```text
apps/web/src/panes.ts                        # + four entries, + why the check exists
apps/web/src/__tests__/panes.test.ts         # the list assertion updated
tests/unit/features/test_pane_features.py    # NEW: the cross-language check
```

**Structure Decision**: the check lives in the Python suite, where the registry
is. It parses the pane list out of the TypeScript source, which is the only
place the two halves meet.
