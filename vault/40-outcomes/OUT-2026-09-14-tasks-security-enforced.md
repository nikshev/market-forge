---
id: OUT-2026-09-14-tasks-security-enforced
step: tasks
records: [REQ-WP-072]
commit: null
---

## What was done

Broke [[REQ-WP-072]] into 45 tasks across eleven phases in
`specs/113-security-enforced/tasks.md`, then ran the cross-artifact analysis.
Eight inconsistencies, two HIGH. All eight fixed.

## What was decided

**A second task that could not pass was caught before it was written.** T024 was
to prove a rate-limit refusal is immediate "by driving it with a clock that would
advance if anything slept". A controlled clock does not advance on a real sleep,
so the task could not test its own criterion — and the criterion behind it,
SC-003's "same order of magnitude of time as a served request", is a wall-clock
assertion in a unit test, which measures the machine rather than the design. Both
now state the checkable claim: the refusal is a `429` carrying `Retry-After`, not
a `200` that arrived late. This is the second cycle running in which the analysis
pass caught a mandated test that was impossible rather than merely wrong.

**The spec still described the approach planning had rejected.** FR-007 read "a
test fails if a credential-bearing value can reach a log record" — the lint that
was rejected for catching one spelling of the mistake. What is being built is a
configuration object that cannot render a credential at all. FR-007, User Story
4's title, and an edge case about grepping for `logging` all described the old
design; all three now describe the built one.

**User Story 4 is promoted to P1 in the spec, not just in the tasks.** Leaving
the tasks saying "the spec marks this P2, but…" would have left two documents
disagreeing about which work matters most, with a footnote as the only bridge.
Planning measured a present defect; the spec now says so.

**Configuration is refused where configuration is read.** The tasks had
`settings_from_env` parsing the origins and `api/security.py` defining
`WildcardOrigin` — two plausible homes and no decision. It raises in
`settings.py`, beside `MissingConfiguration`, which already refuses rather than
defaults. `api/security.py` holds only middleware.

**A new edge case the real design has**, replacing the one the rejected design
had: a password containing `@` or `:` defeats a mask that splits the URI on
punctuation, and defeats it silently. T009 pins it, and T010 says to parse the
URI rather than split it.

**SC-006 gained a task.** "The suite runs with no services and no network" was a
success criterion nothing checked.

## What is still open

Nothing from the analysis. The items carried from planning stand: what the
limiter keys on behind a proxy stays the address the application sees, and
`docs/deployment.md`'s three stale prose claims are corrected by hand because
the test that guards that document checks names, not sentences.
