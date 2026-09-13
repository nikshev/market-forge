---
id: REQ-PHASE-8
title: Production hardening
type: phase
prd_ref: "Phase 8 — Production hardening"
prd_lines: "6904-6917"
phase: 8
status: planned
depends_on: ["REQ-PHASE-7A"]
tags: []
covers: [REQ-WP-064, REQ-WP-065, REQ-WP-066, REQ-WP-035, REQ-WP-036, REQ-WP-037, REQ-WP-038, REQ-WP-039, REQ-WP-041, REQ-WP-042, REQ-WP-055, REQ-WP-056, REQ-WP-057]
not_delivered:
  - "load generation against a deployment: [[REQ-WP-057]] measures §36's targets and guards the scaling that would break them; [[REQ-WP-064]] made the API and the web app deployable and nothing drives concurrent traffic at them yet"
---

## Requirement

Deliverables:

- Redpanda/Kafka optional;
- S3 cold retention;
- monitoring dashboards;
- alerting on data outages;
- backup/restore;
- deployment docs;
- load tests.

---

## Acceptance

- the stream transport can be switched off and the system still runs end to end (§45 calls it optional);
- cold retention writes an object and reads it back byte-identical (§29);
- every metric §33 names is exported, and a metric with no source is absent rather than reported as zero;
- a data outage raises an alert naming the feed and the gap, and the affected feature family moves to `STALE` rather than continuing to serve (§32, §33);
- a backup restores into an empty database and replays to the same state (§35.5's parity standard applied to storage);
- deployment documentation brings the stack up from a clean machine (§37);
- load tests demonstrate §36's targets, and a target that is not met is reported rather than omitted;
- no secret is committed, and secrets are redacted from logs (§34).

_Derived, not quoted: the PRD states no acceptance criteria for this phase. Each line names the section it comes from; the derivation is recorded in `docs/superpowers/specs/2026-09-09-phase-acceptance-design.md`._

## Coverage

Which requirements deliver this phase, and what nothing delivers. The
`covers:` and `not_delivered:` frontmatter carries the same two lists, and
`tests/tools/trace/test_phase_coverage.py` checks that every covering
requirement exists and has reached `implemented`.

**Delivered by:**

_Nothing in this repository delivers any part of this phase._

**Not delivered:**

- Redpanda/Kafka optional transport: not built
- S3 cold retention: MinIO is provisioned for the dev stack, with no retention tiering
- monitoring dashboards: no metrics are exported
- alerting on data outages: the alerting layer sends trading signals, not operational alerts
- backup/restore: not built
- deployment docs: the repository documents development, not deployment
- load tests: not built

This phase is `planned` rather than `implemented` because that list is not
empty. A phase is its deliverables; a phase with a missing deliverable is a
phase in progress, however much of it is built.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-051-phase-coverage]]
- **Tests:**
    - `tests/tools/trace/test_phase_coverage.py::test_phase_8_coverage`
- **Outcomes:** [[OUT-2026-09-09-implement-phase-coverage]], [[OUT-2026-09-09-requirement-phase-acceptance]], [[OUT-2026-09-09-spec-phase-coverage]]
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
