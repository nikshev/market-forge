# Implementation Plan: No centred filter reaches a live feature

**Branch**: `bias-002-live-causality` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/058-live-causality/spec.md`

## Summary

Widen two guards that already exist, and read a field that is already required.

- The forbidden-import scan moves from one package to every module under
  `src/channelflow/`, with a per-module exemption list that carries reasons and
  fails when it goes stale.
- `FeatureSpec.point_in_time_safe` becomes `Literal[True]`, so a feature that is
  not point-in-time safe cannot be registered at all rather than being registered
  and caught later.

Nothing new is invented. [[ADR-022]] settled that a general detector is not
achievable, and this does not attempt one.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new. `channelflow.extrema.causality` and `channelflow.features.registry` as they stand.

**Storage**: none.

**Testing**: pytest, `@pytest.mark.trace("REQ-BIAS-002")`; a mutation sweep over the scan.

**Target Platform**: library.

**Project Type**: single project.

**Performance Goals**: none. The scan reads 27 packages' sources once per suite run.

**Constraints**: `causality.py` must keep naming the forbidden helpers in order to forbid them, which is the exemption list's first and only entry today.

**Scale/Scope**: 27 packages, ~1 exemption, 1 registry field narrowed.

## What the survey found

Run before planning, and it changed the design:

- **Only one file in the repository holds a forbidden helper**, and it is
  `extrema/causality.py`, which names them to forbid them. No research module
  imports one — `derivative_turning` writes its own centred labeller rather than
  reaching for `savgol_filter`.
- So **no research exemption is needed today.** Pre-exempting `research/` because
  PRD §13A.6 permits centred filters there would weaken the rule for a case that
  does not exist. The list stays empty of it until something needs it.
- And **the exemption is per module, not per package.** The only real case is one
  file; exempting the `extrema` package would have exempted every module beside
  it, including the ones this rule most wants scanned. The spec was amended to
  match, which is the survey doing its job.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Bearing | Verdict |
|---|---|---|
| **I. No look-ahead, ever** | The rule this implements is one of §41's statements of Principle I. | **Pass, and it is the point.** |
| **VI. Every feature is documented** | `point_in_time_safe` narrows from a field an author fills in to a claim the type enforces. | **Pass.** The author still writes it, so [[ADR-015]]'s "no field an author can forget to think about" survives. |
| **XII. Correctness precedes performance** | A scan of 27 packages' sources per suite run. | **Pass.** Milliseconds, and named here so nobody has to wonder. |
| **XIV. Everything is traceable** | The exemption list is policy and belongs in source, not in a test. | **Pass.** It lives in `causality.py` carrying the requirement's marker. |

No violations; Complexity Tracking removed.

## Project Structure

### Source Code (repository root)

```text
src/channelflow/extrema/causality.py   # + EXEMPT, + forbidden_in(); @trace: REQ-BIAS-002
src/channelflow/features/registry.py   # point_in_time_safe: Literal[True]
tests/unit/extrema/test_live_causality.py   # NEW: the widened scan
```

**Structure Decision**: the policy — which helpers are forbidden, and which
modules are exempt and why — lives in `causality.py` beside the guard it belongs
to. The walk over the tree lives in the test, as the existing Test D's does: it
is a check on the repository, not a function the engine calls.
