# Implementation Plan: A replay records the extrema it detected

**Branch**: `wp-029-record-extrema` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Two events, one recorder, and a detector pass inside `record_replay`.

`ExtremumObserved` and `ExtremumConfirmed` join the bus; `ExtremumRecorder`
subscribes to both and writes each kind in one batch; `_detect` runs the
detector over the same bars and publishes as it goes.

## Did the bus survive a second producer?

Yes, unchanged. The spec pre-committed to calling any change a finding about the
bus, and there is none to report: `subscribe` and `publish` took a second
producer and two more consumers without a line moving. The one thing that
mattered — that a subscription made during a dispatch does not receive that
dispatch — never came up, because the recorders subscribe before anything is
published.

That is a weaker endorsement than it sounds and worth saying plainly: the second
producer publishes into the same bus instance in the same thread on the same
pass. It exercises the seam, not the hard parts of one.

## Technical Context

**Language/Version**: Python 3.12 · **Dependencies**: none new · **Storage**: [[REQ-WP-028]]'s two tables

**Testing**: pytest with `@pytest.mark.trace("REQ-WP-029")`, plus a mutation sweep.

**Constraints**: per-bar publishing; watermarks on knowledge, not on the turn.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VII. Live and replay are the same code** | A live process attaches the same subscribers to the same events. | **Pass**, and FR-005 is what keeps it true. |
| **III. History is immutable** | Extrema go on the append-only plane. | **Pass**, with [[ADR-056]]'s watermark. |
| **IX. Deterministic in backtest mode** | A second pass over the same list. | **Pass.** The detector is deterministic and its ids are derived. |

No violations.

## Project Structure

```text
src/channelflow/events.py            # + ExtremumObserved, ExtremumConfirmed
src/channelflow/pipeline/replay.py   # + ExtremumRecorder, _detect, Recording counts
tests/unit/pipeline/test_record_extrema.py  # NEW
```

**Structure Decision**: the detector gets its own pass. The runner owns its loop
and offers no per-bar hook; adding one to feed a detector would change a
component with nothing to do with extrema.
