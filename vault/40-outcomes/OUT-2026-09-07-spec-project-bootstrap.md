---
id: OUT-2026-09-07-spec-project-bootstrap
step: spec
records: [REQ-WP-001]
commit: null
---

## What was done

REQ-WP-001 specified as `specs/002-project-bootstrap/spec.md`. First forward
run of the SDD pipeline — REQ-INFRA-001 was retroactive, so this is the first
requirement specified before its implementation exists.

## What was decided

- **The dev stack is backing services only.** "One command starts dev stack" was
  ambiguous between infrastructure, infrastructure plus API, and everything
  including the frontend dev server. Chosen: PostgreSQL and MinIO only. The API
  and workers run from the host until there is code to containerise, which keeps
  the tested criterion simple — connect to each service and perform a real
  operation.
- **No analytical database.** Recorded separately as [[ADR-002]]: ClickHouse is
  dropped and the PRD's target storage profile adopted from the start.
- **MinIO rather than a local directory** for object storage. The target profile
  makes S3-compatible storage the canonical data plane; a filesystem stand-in
  would reintroduce exactly the local-versus-production divergence Principle VII
  forbids. This is a judgement call, recorded in ADR-002 so it can be reversed.
- **Frontend scaffold now, charts later.** PRD WP-001 lists a frontend scaffold
  and PRD §7 names React/TypeScript/Vite. Lightweight Charts is excluded — it
  belongs to REQ-WP-009. Building the shell now fixes toolchain versions while
  they are still free to change.
- **mypy in strict mode over the product source tree.** PRD §7 leaves the type
  checker optional. Chosen because conflating `event_time` with `ingest_time` is
  exactly the class of error PRD §0.3 forbids, and types catch it at authoring
  time rather than in a backtest.
- **Twelve functional requirements and six success criteria** derived from a
  single-line acceptance criterion ("one command starts dev stack"). The
  expansion is deliberate: the criterion says nothing about idempotence, health
  conditions, data persistence, or what happens when a port is taken, and all
  four are things a developer hits on day one.

## What is still open

- **Postgres schema and migrations** are out of scope here; REQ-WP-002 brings
  the domain model, and the migration tool has not been chosen.
- **No CI configuration.** The commands defined here are what CI would run, but
  nothing runs them automatically yet. Deliberate — there is no remote gate to
  wire up until the work lands somewhere shared.
- **Application services are not containerised.** Phase 0's acceptance says
  "services boot locally", which this satisfies for backing services only. If
  that reading is wrong, it surfaces when REQ-PHASE-0 is closed, not here.
- **Pinot is deferred indefinitely.** ADR-002 defers it until a HOT serving
  requirement exists. No requirement currently states one.
