# Implementation Plan: One research run, end to end

**Branch**: `wp-024-research-run` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

`pipeline/study.py`'s `run_study` composes five existing mechanisms. Two of them
had to change to be composable, and both changes are findings rather than
conveniences:

- **`Score` gains an optional artifact**, so a comparison reports what it fitted
  and the run does not refit. Refitting to obtain a hash would be a second
  scoring path.
- **`report_comparison` accepts one artifact per variant.** A comparison that
  fits its variants gives each a different artifact, and a single value would
  have recorded several models under one hash.
  [[SPEC-057-experiment-gate-adoption]] pre-committed to calling that a finding
  about the gate rather than absorbing it, so it is recorded as one.

## Technical Context

**Language/Version**: Python 3.12 · **Dependencies**: none new · **Storage**: two existing lakehouse tables

**Testing**: pytest with `@pytest.mark.trace("REQ-WP-024")`, plus a mutation sweep across three modules.

**Constraints**: the dataset reference and code version are the caller's; nothing here reads git, a clock or a store for identity.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **XI. Results are reproducible** | All four of §0.13's hashes are assembled here for the first time. | **Pass, and it is the point.** |
| **XIV. Everything is traceable** | Five mechanisms gain their first caller. | **Pass.** |
| **IV. Baselines before models** | The winner must beat the base rate or nothing is promoted. | **Pass.** |
| **XII. Correctness precedes performance** | Every model is hashed on every fold. | **Pass.** Milliseconds, and named so nobody wonders. |

No violations.

## Project Structure

```text
src/channelflow/pipeline/study.py       # NEW
src/channelflow/models/report.py        # Score.artifact; compare reports it
src/channelflow/models/registry.py      # combined_artifact
src/channelflow/models/base.py          # BaseRate remembers it was fitted
src/channelflow/experiments/fields.py   # report_comparison takes a mapping
tests/unit/conftest.py                  # moved up from tests/unit/turning/
tests/unit/pipeline/test_study.py       # NEW
```

**Structure Decision**: the run lives in `pipeline/`, beside `replay.py`. That
package is already where producers are wired to consumers; a study wired to the
registries is the same shape for research.
