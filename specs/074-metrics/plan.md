# Implementation Plan: A metric nobody writes is absent, not zero

**Branch**: `wp-036-metrics` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

`channelflow/metrics.py`: a registry that holds only what has been observed, a
renderer that emits Prometheus text, and two derivations over data that already
exists — delivery failures from the dispatcher audit, stale feed count from
[[REQ-WP-035]]'s assessments.

The registry's central property is what it does **not** do: registering a metric
does not create a series. A series exists when something observes it, and until
then the metric is absent from the exposition.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new, deliberately

**Testing**: unit tests over the registry, the format and the derivations; a
mutation sweep. The existing suites are the regression floor.

**Constraints**: no clock ([[ADR-018]]); no global registry; names validated at
registration.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VII. Live and replay are the same code** | Every instant is an argument, so a replay produces the same numbers. | **Pass.** |
| **VI. Every feature is documented** | The unimplemented metrics are named, not hidden. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-036`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/metrics.py            # NEW: registry, exposition, derivations
tests/unit/metrics/test_registry.py   # NEW
```

**Structure Decision**: one module. A registry, a renderer and two derivations
are one idea, and splitting them across a package would put three files where a
reader wants one paragraph.

## Registering without creating

`register` records a name, a type and a help string. It does not create a series
and does not make the metric appear. `observe` creates the series.

The distinction is the requirement, and it is easy to lose: nearly every metrics
library initialises a registered counter to zero, which is convenient in a
long-running process where everything is eventually incremented, and dishonest
in one where half the producers do not exist. A test asserts the empty
exposition of a registry with eleven registered metrics and nothing observed.

## The derivations

`delivery_failures(audit)` counts records whose status is not `delivered`, and
`stale_feeds(healths)` counts assessments whose state is not GOOD. Both read
structures the system already produces, rather than a parallel counter someone
must remember to bump — a counter like that silently stops when a new code path
forgets it, and the metric stays flat while the thing it measures gets worse.
