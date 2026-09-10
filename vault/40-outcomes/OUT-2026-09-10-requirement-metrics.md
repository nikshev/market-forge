---
id: OUT-2026-09-10-requirement-metrics
step: requirement
records: [REQ-WP-036]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-036.md`, extracted from PRD §33 and §45's
Phase 8. Part of [[REQ-PHASE-8]]'s "monitoring dashboards" deliverable.

## What was decided

- **The requirement is one rule in the place it hurts most.** A metric nobody
  writes must be absent, not zero. On a dashboard a stuck zero is
  indistinguishable from a healthy zero, every alert built on it stays green
  forever, and the failure is then invisible *and* believed to be watched. That
  is worse than having no dashboard, because a missing dashboard gets noticed.
- **Eleven metrics are listed and a few have producers.** Exporting all eleven
  so the board looks complete is the failure above, performed on purpose.
- **The two that do have producers are derived, not bumped.** Telegram delivery
  failures come from the dispatcher's audit and stale feed count from
  [[REQ-WP-035]]'s assessments. A parallel counter someone must remember to
  increment is a metric that silently stops when a new code path forgets.
- **Counters refuse to decrease.** A clamped decrement is a lie told quietly; a
  refusal is a bug report.
- **Scope is the exposition, not the dashboards.** A Grafana definition
  describes a deployment that does not exist yet, so half of §45's deliverable
  stays in `not_delivered` where it can be argued with.

## What is still open

- **Most of §33's list has no producer**, because no connector or pipeline runs.
  The requirement asks for them to be named in one place rather than faked.
- **The scrape endpoint itself.** Whether the exposition is served over the
  existing API or by a separate process is a deployment question, and deployment
  is another Phase 8 deliverable.
