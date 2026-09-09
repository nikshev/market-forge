# Implementation Plan: Comparing the channel that existed against the model's later state

**Branch**: `us-003-repaint-comparison` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One module and one endpoint: the stored snapshot at an instant beside a refit
over history up to a later one, with every delta measured and the hindsight
span stated.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `api.channels` for both views, `channels` for the
production fitter. Nothing new.

**Testing**: pytest over the repository and the test client.

**Target Platform**: `src/channelflow/api/`.

**Constraints**: FR-009 and FR-010 ([[ADR-046]]).

**Scale/Scope**: 1 module, 1 endpoint, 13 tests.

## Constitution Check

- **I (no look-ahead)** — the hindsight here is the subject of the measurement,
  not an input to a feature. It is stated in nanoseconds on every answer, the
  payload declares itself research-only, and a test asserts no signal-path
  module imports the module at all.
- **VI (every feature is documented)** — both channels report their model and
  version, so a difference can be attributed.
- **XIV** — traces to REQ-US-003.

**Gate result: PASS**, with Principle I's exception argued above and recorded in
[[ADR-046]].

## Project Structure

```text
src/channelflow/api/
├── comparison.py   # NEW: the two channels and their difference
├── schemas.py      # + ChannelComparisonOut, ChannelDifferenceOut
└── routes.py       # + GET /channels/comparison
```

**Structure Decision**: its own module, beside `channels.py` rather than inside
it. `channels.py` serves one view at a time and caps every fit at the requested
instant; this one deliberately does not, and mixing the two would put a
hindsight path inside the module whose docstring promises there is none.

## Approach

**`now_ns` is an argument, never a clock.** PRD §27.5 refits over
"visible/current history", and what is visible is the reader's window. An
argument also makes the test suite able to ask for a fixed span, which a clock
reading would not.

**Both refusals are the existing ones.** A missing snapshot and an unfittable
history already raise `ChannelUnavailable` in `channels.py`; this module adds
one refusal of its own, for a "later" instant that is earlier.

**The width-relative figure is `None`, not infinity.** A hundred dollars of
repaint means one thing on a five-hundred-wide channel and another on a
five-wide one, so the ratio is the comparable number — and on a zero width it is
not a number at all.

**The import ban is checked over import lines, not over the word.**
"Comparison" is ordinary English and appears in these packages' prose; a check
that failed on a docstring would be renamed away rather than fixed, and would
then be checking nothing.

## Complexity Tracking

> No violations.
