---
id: OUT-2026-09-08-implement-trace-rule-r8
step: implement
records: [REQ-INFRA-001, REQ-INFRA-002]
commit: null
---

## What was done

Validator rule **R8**: a requirement at `implemented` or above needs at least
one `IMPLEMENTS` edge — some git-tracked source file carrying `# @trace: <id>`.

Code collection now also reads `.github` and YAML files.

## What was decided

- **The hole was found by using the gate, not by reading it.** REQ-WP-010 was
  marked `implemented` with sixteen passing tests and no marker in any source
  file, and `make validate` printed `trace: clean`. R2 asks whether tests
  exist; nothing asked whether what they test can be traced. The graph's whole
  reason for existing is request → test → implementation, and half of it could
  be missing silently.
- **R8 then flagged REQ-INFRA-002 immediately, and it was right.** That
  requirement is implemented by `.github/workflows/ci.yml` and nothing else,
  and collection was Python-only — so a gate written in YAML was invisible to
  the graph that is supposed to prove gates exist. Extending collection was the
  fix; narrowing R8 would have been the cover-up.
- **Mutation-checked both directions.** Removing the rule fails its own test;
  removing the markers from `src/channelflow/backtest/` fails the real repo's
  `make validate`.

## What is still open

- Nothing from this step. `Makefile` still carries no marker: R8 is satisfied
  per requirement, not per file, and the workflow already names the gate.
