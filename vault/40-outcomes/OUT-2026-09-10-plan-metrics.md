---
id: OUT-2026-09-10-plan-metrics
step: plan
records: [REQ-WP-036]
commit: null
---

## What was done

`specs/074-metrics/`: `plan.md`, `research.md`, `data-model.md`,
`contracts/exposition.md`, `quickstart.md`. [[REQ-WP-036]] moves to `planned`.

## What was decided

- **Registering does not create a series; observing does.** This is the whole
  requirement in one behaviour, and it is the opposite of what nearly every
  metrics library does. Their default is convenient in a process where
  everything is eventually incremented and dishonest in one where half the
  producers are not written yet.
- **No client library.** The official one assumes a module-level global
  registry, a process collector and a clock — the three things [[ADR-018]] and
  this codebase's testing style have spent requirements removing. It would also
  default a registered counter to zero, which is the single behaviour being
  prevented.
- **`COUNTER` and `GAUGE` only.** A histogram needs bucket boundaries nobody has
  chosen, and choosing them here would be a research default wearing a
  decision's clothes.
- **Label values are escaped.** A reason string reaching a label unescaped
  breaks the line, and Prometheus then drops the sample or reads it as a
  different series — a monitoring failure whose symptom is a quiet dashboard.

## What is still open

- Nothing new. The three from [[OUT-2026-09-10-spec-metrics]] stand: most of
  §33 has no producer, the scrape endpoint is a deployment question, and whether
  the unimplemented list should fail a test on PRD drift.
