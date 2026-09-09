# Implementation Plan: Structural extremum detector comparison

**Branch**: `exp-011-extremum-detector` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module running [[REQ-WP-019]]'s detector under each of its five
threshold modes, plus the one change that made the fifth mode reachable at all.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.extrema`, `channelflow.backtest`.

**Testing**: pytest, over a smooth swing series, a choppy one, and two with
regime changes.

**Target Platform**: `src/channelflow/research/`, with a parameter added to
`extrema/detector.py` and a unit fix in `extrema/thresholds.py`.

**Constraints**: FR-003 and FR-004 (the channel width), FR-011 (no ranking).

**Scale/Scope**: 1 module, 17 tests.

## Constitution Check

- **VII (live and replay are the same code)** — every method runs through the
  production detector.
- **X (thresholds are configuration)** — the policy's own modes, unchanged.
- **XI (results are reproducible)** — no sampling; the regime split is the
  series' own median.
- **XIV** — traces to REQ-EXP-011.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/extremum_detectors.py   # NEW
src/channelflow/extrema/detector.py              # + channel_width_pct on on_bar
src/channelflow/extrema/thresholds.py            # width read as a percentage
```

**Structure Decision**: the channel width is passed in rather than fitted by the
detector. The detector holds bars; a channel is a model with its own lookback
and refusals, and a detector that fitted one would own a dependency the whole
package has avoided.

## Approach

**The fifth mode was unreachable.** `CHANNEL_WIDTH_FRACTION` needs a width, and
`on_bar` had no way to supply one — so the mode existed in the policy and could
never fire through the detector. It takes an optional argument now.

**And its units were a trap.** The parameter was named `_pct` and read as a
fraction of price, while the only producer of that number is
`ChannelSnapshot.width_pct`, a percentage. The two differ by a hundred, and the
failure is silent: a real channel makes the threshold a hundred times too wide
and the detector simply stops confirming.

**Nothing is ranked.** The five metrics pull against each other by construction.

**The regime split is the series' own median**, so it divides any shape in half;
a cut taken from one bar's reading lands wherever that bar happened to be.

## Complexity Tracking

> No violations.
