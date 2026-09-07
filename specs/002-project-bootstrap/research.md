# Research: Project Bootstrap

Decisions that needed a reason rather than a default, and what was rejected.

## Container image tags

**Decision**: pin both images to explicit minor versions — `postgres:16-alpine`
and a dated MinIO release tag — never `latest`.

**Why**: Principle XI requires a result to be reproducible from a commit hash. A
`latest` tag makes the stack a moving target: a checkout from six months ago
brings up whatever the registry serves today, and a bug that reproduces on one
machine may not on another.

**Rejected**: digest pinning (`@sha256:...`). It is stricter still, but it makes
routine patch upgrades a manual lookup, and the reproducibility gap between a
minor tag and a digest is small next to the friction. Revisit if a patch release
ever breaks the stack.

## PostgreSQL 16

**Decision**: PostgreSQL 16.

**Why**: PRD §7 names PostgreSQL in both the MVP and target profiles without a
version. 16 is the current stable line, and nothing in §30's data model needs a
17-only feature.

**Rejected**: 17, on the grounds that the newest major buys nothing here and
narrows the set of managed offerings available later.

## MinIO rather than a local directory

**Decision**: run MinIO as a container.

**Why**: recorded in ADR-002 and referenced by the plan's Constitution Check.
The target storage profile makes S3-compatible object storage the canonical data
plane, so a filesystem stand-in would mean writing and testing against one
interface and deploying against another — the divergence Principle VII exists to
prevent.

**Rejected**: a local `data/` directory, which is simpler today and wrong the
moment anything writes Parquet through an S3 client.

## Strict typing scope

**Decision**: `mypy --strict` over `src/` only.

**Why**: `src/channelflow/` is where the code that must not conflate
`event_time` with `ingest_time` will live — PRD §0.3 and §0.4 make that class of
error a stated hazard, and types catch it at authoring time. The existing
`tools/trace/` package predates this decision.

**Rejected**: strict typing over `tools/` as well. Retrofitting it is real work
with no bearing on market-data correctness, and folding it into a bootstrap
feature would hide that cost. If it is worth doing it deserves its own
requirement.

**Rejected**: `pyright`. Faster and better in-editor, but it pulls Node into the
Python backend's toolchain for a benefit that does not show up in CI.

## Health conditions

**Decision**: both services declare a health condition, and the start command
does not report success until each is healthy.

**Why**: SC-002 measures that the command reports success only after each
service answers a real request. A container that has started is not a service
that is ready — PostgreSQL in particular accepts TCP connections before it will
serve queries, so a naive start reports success into a race.

**Rejected**: a fixed sleep, which is either too short on a cold start or wasted
time on a warm one, and never tells you which.

## No application service in the stack

**Decision**: the API and workers run from the host during development; only
backing services are containerised.

**Why**: containerising an application that does not exist yet means writing a
Dockerfile and a hot-reload mount for no code. It also keeps the acceptance
criterion honest — "one command starts dev stack" is testable by connecting to
two services, with nothing to mock.

**Rejected**: containerising the API now, which the spec's Assumptions record as
a possible different reading of Phase 0's "services boot locally". If that
reading is the right one, it surfaces when REQ-PHASE-0 is closed, and adding a
service to a working compose file is cheap.
