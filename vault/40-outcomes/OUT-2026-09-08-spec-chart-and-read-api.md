---
id: OUT-2026-09-08-spec-chart-and-read-api
step: spec
records: [REQ-API-001, REQ-WP-009]
commit: null
---

## What was done

`specs/013-chart-and-read-api/spec.md`: four user stories, 17 functional
requirements, 10 success criteria, three ADRs.

## What was decided

- **Both requirements are specified together, because neither is testable
  alone.** An API with no consumer and a chart with no data are each testable
  only in the trivial sense. The property that matters — a deep link opening
  the instant it names in the mode PRD §27.5 requires — needs both halves.
- **A repository port, not a database** ([[ADR-019]]). PRD §29's storage is
  unbuilt and REQ-WP-009 cannot wait for it. The port is also where FR-017's
  point-in-time rule becomes a signature rather than a convention every
  endpoint has to remember.
- **`AS-SEEN-THEN` defaults everywhere, and the chart says which mode it is in**
  ([[ADR-020]]). A default drifting to false would turn every deep link into a
  refit — including the links in every alert already sent — and old signals
  would start looking better than they were.
- **The frontend is gated in CI, not in pre-commit** ([[ADR-021]]). `npm ci` on
  every commit would break the property REQ-INFRA-002 exists to protect. The
  rule "no check may be absent from both gates" is honoured narrowly: each
  frontend check runs in exactly one.

## What is still open

- **`min_score` and `setup_type` filters are not implemented.** Both need PRD
  §43's ranker; they stay in REQ-API-001's text as what is owed.
- **§27.2's other overlays, §27.3's lower panes and §27.4's explanation panel
  are out of scope** — REQ-WP-009's acceptance names four layers.
- **No authentication.** The API is not publicly exposed in this phase, and
  inventing a scheme the PRD does not specify would be worse than leaving the
  boundary explicit.
