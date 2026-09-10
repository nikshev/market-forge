---
id: OUT-2026-09-10-plan-stop-alert
step: plan
records: [REQ-WP-034]
commit: null
---

## What was done

`specs/072-stop-alert/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/notification.md`, `quickstart.md`. [[REQ-WP-034]] moves to `planned`.

## What was decided

- **`stop_in_force` is carried, not derived.** Deriving it would mean the
  notification re-deciding what was active, and that is the replay's answer to
  give. A field also makes the wrong value visible at a call site rather than
  buried in a calculation.
- **One dispatcher, made kind-agnostic**, at the cost of a deferred import in
  `models.py`. The two alternatives are worse: moving PRD §26.1's renderer into
  the frozen record puts a formatter inside a data model, and a second
  dispatcher copies the retry, dead-letter, audit and never-block behaviour
  §26.4 specifies once. Duplicated retry logic diverges silently, and the
  failure is one alert kind quietly not being retried — visible only in an audit
  nobody reads until something has already been missed.
- **The stop notification is its own module.** Adding a second kind inline would
  turn `models.py` and `render.py` into "alerts, plural" and leave a reader
  working out which half applies to which.
- **Both risk figures floor at zero.** A stop past entry has no open risk left,
  and zero there is a reading.

## What is still open

- Nothing new. The three from [[OUT-2026-09-10-spec-stop-alert]] stand: when the
  notification fires, where the deep link points, and that nothing constructs a
  dispatcher outside the package.
