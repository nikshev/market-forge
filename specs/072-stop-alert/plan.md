# Implementation Plan: A stop update is announced with the risk it changed

**Branch**: `wp-034-stop-alert` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

A second kind of notification, and one change to make room for it: the
dispatcher stops knowing what an `Alert` is.

`StopUpdateAlert` carries the position, the proposal, and **the stop that was in
force** — the third of those being the whole of FR-003. Its renderer produces
§44A.34's message, in which every line is a transition. A gate decides what is
worth saying: a move always, a hold or refusal only under debug, and never in
the shape of an update.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: the existing alerting suite is the regression floor; new tests for
the transition, the gate, and the shared audit. Mutation sweep over both.

**Constraints**: [[ADR-016]] (absent, never dashed), [[ADR-017]] (ids derived,
never generated), [[ADR-018]] (no clock, no sleep, nothing escapes into the
caller).

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VII. Live and replay are the same code** | The id is derived from the position and the decision instant, so a replay produces the same notification. | **Pass.** |
| **VI. Every feature is documented** | Reasons reach the message verbatim. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-034`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/alerting/dispatch.py       # Notification protocol; Dispatcher stops importing render
src/channelflow/alerting/models.py         # Alert gains notification_id / symbol / render / link
src/channelflow/alerting/stop_updates.py   # NEW: StopUpdateAlert, its renderer, its gate
src/channelflow/alerting/__init__.py       # + the exports
tests/unit/alerting/test_stop_updates.py   # NEW
```

**Structure Decision**: the stop notification is its own module rather than more
of `models.py` and `render.py`. Those two are PRD §26's signal alert; a second
kind added inline would make both files "alerts, plural" and leave a reader
guessing which half applies to which.

## The one structural change, and its cost

`Dispatcher` renders an `Alert` today. It will render a `Notification` — anything
that can identify itself, name its instrument, render, and link.

The cost is a deferred import: `models.py` will call `render.py`, which imports
`models.py`. Two lines inside a method with a comment saying why, rather than
moving PRD §26.1's renderer into the model, which would mix a formatter into a
frozen record, or a second dispatcher, which would duplicate the retry and
dead-letter behaviour §26.4 specifies once. Duplicated retry logic diverges
silently, and the divergence surfaces as one alert kind quietly not being
retried.
