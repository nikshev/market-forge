---
id: OUT-2026-09-10-spec-metrics
step: spec
records: [REQ-WP-036]
commit: null
---

## What was done

`specs/074-metrics/spec.md`: three user stories, 10 functional requirements,
6 success criteria. [[REQ-WP-036]] moves to `specified`.

## What was decided

- **FR-001 and FR-002 together are the specification.** Absent stays absent, and
  an observed zero is present. Either alone is satisfiable by an implementation
  that gets the other wrong, and only the pair makes a dashboard honest — which
  is why SC-001 asserts them in one criterion rather than two.
- **FR-008 names what does not exist.** Normally that is scope creep. Here it is
  the only alternative to the two failures this spec is about: exporting an
  unproduced metric as zero, or dropping it from the list so nobody notices it
  is missing.
- **No client library.** A Prometheus client would import a global registry, a
  process collector and a clock — three things this codebase has spent
  requirements removing. The exposition format is a few lines of text.
- **SC-002 names Prometheus deliberately.** §33 says "Prometheus-compatible", so
  the format is part of the requirement rather than a technology choice being
  made here.

## What is still open

- **Most of §33's list has no producer.** The requirement asks for those to be
  named rather than faked.
- **The scrape endpoint.** Serving the text is a deployment question, and
  deployment is another Phase 8 deliverable.
- **Whether the unimplemented list should fail a test when §33 gains a metric.**
  It would catch drift, and since the PRD is read-only the drift could only come
  from a re-extraction.
