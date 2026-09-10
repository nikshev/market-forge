# Implementation Plan: One event bus between producers and consumers

**Branch**: `infra-003-event-bus` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

A small synchronous bus, and the replay path rewired to use it.

The decision that makes this more than decoration: **each producer receives one
publishing hook, and every consumer subscribes.** Today `BarBuilder` is handed
the collector, and the runner is handed the two recorders. After this, all three
are handed `bus.publish` and the recorders subscribe — so a second consumer is a
subscription rather than a change at the producer's construction site, which is
the only cost the current wiring actually has.

The alternative shape — keep the hooks and publish alongside them — would have
satisfied the deliverable's wording while leaving that cost exactly where it is.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new.

**Storage**: none. The bus does not persist or buffer; [[ADR-002]]'s canonical plane is where durability lives.

**Testing**: pytest, `@pytest.mark.trace("REQ-INFRA-003")`; a mutation sweep over dispatch.

**Project Type**: single project.

**Performance Goals**: none. One dict lookup and a list walk per event.

**Constraints**: dispatch synchronous and in subscription order (Principle XI); a subscriber's exception propagates.

**Scale/Scope**: one new module, one events module, `pipeline/replay.py` rewired.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **XI. Results are reproducible** | A reordering bus breaks replay determinism while looking like plumbing. | **Pass**, and it is why FR-004 is a requirement rather than a design note. |
| **VII. Live and replay are the same code** | The bus is the seam a live process would publish into. | **Pass.** Not built here; the shape does not preclude it. |
| **XIII. Work is incremental** | A bus with no subscriber is speculative generality. | **Pass.** Its only consumer exists on day one, and the spec pre-commits to calling it a finding if that consumer reads worse. |
| **IX. Code must be deterministic in backtest mode** | Same as XI, from the other side. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/bus.py          # NEW: EventBus
src/channelflow/events.py       # NEW: BarFinalized, ChannelFitted, CandidateUpdated
src/channelflow/pipeline/replay.py   # rewired: producers publish, recorders subscribe
tests/unit/test_bus.py          # NEW
tests/unit/pipeline/test_replay.py   # + the recorded output is unchanged
```

**Structure Decision**: `bus.py` holds the mechanism and knows no domain type;
`events.py` holds the values and knows no bus. Neither imports `pipeline`, so a
live process can publish the same events without reaching through the replay
path.
