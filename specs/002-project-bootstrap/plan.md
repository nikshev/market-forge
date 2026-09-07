# Implementation Plan: Project Bootstrap

**Branch**: `002-project-bootstrap` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-project-bootstrap/spec.md`

## Summary

Provision the local development stack and the repository's quality gate for
ChannelFlow. One command brings up PostgreSQL and a MinIO object store, both
health-gated; lint, strict type checking and tests pass green on a clean
checkout; a Vite/React/TypeScript shell builds and type-checks.

No product code, no schema, no API. This feature makes the environment exist so
that REQ-WP-002's domain model has somewhere to live.

## Technical Context

**Language/Version**: Python 3.12 (pinned; PRD §7 says 3.12+, and `.python-version` already pins 3.12). TypeScript 5.x for the web shell.

**Primary Dependencies**: `uv` for Python environment and resolution; `ruff` for lint and format; `mypy` for strict static typing; `pytest` for tests. Vite + React 18 + TypeScript for the web shell. Docker Compose for the service stack. No FastAPI yet — nothing serves anything in this feature.

**Storage**: PostgreSQL 16 (transactional metadata and control plane) and MinIO (S3-compatible object store, the canonical data plane). **No analytical database** — ADR-002 drops ClickHouse and adopts the PRD's target storage profile from the start. DuckDB arrives later as a library, not a service.

**Testing**: `pytest`, plus the repository's existing traceability gate (`make validate`). The stack itself is verified by integration tests that connect to each running service and perform a real operation.

**Target Platform**: Local developer machines (macOS arm64 and Linux x86_64). Production deployment is out of scope.

**Project Type**: Web application — Python backend under `src/channelflow/`, web shell under `apps/web/`, following PRD §37's suggested layout.

**Performance Goals**: None. This feature has no runtime path worth measuring. The only time budget that matters is developer-facing: the stack should reach healthy in well under a minute on a warm image cache.

**Constraints**: The quality gate must be green on a clean checkout (SC-003) — a red baseline teaches people to ignore the gate. Strict typing applies to `src/` only; the existing `tools/trace/` package was written before this decision and retrofitting it is not part of this feature.

**Scale/Scope**: Two containers, one lockfile, four quality commands, one empty web page. Roughly a dozen files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Most of the constitution governs market-data correctness and has no surface in a
bootstrap feature. Recording that honestly matters more than ticking fourteen
boxes: a Constitution Check that claims every principle applies teaches the
reader that the check is theatre.

**Principles that bind this feature:**

- **VII (live and replay are the same code)** — the reason the object store is a
  MinIO container rather than a local directory. Developing against a filesystem
  and switching to S3 later reintroduces exactly the local-versus-production
  divergence this principle forbids. Recorded in ADR-002.
- **X (thresholds are configuration)** — service credentials, ports and
  connection settings live in an environment file with a committed example
  carrying development-only defaults. No credentials in code, none committed.
- **XI (results are reproducible)** — dependency versions are pinned and a
  lockfile is committed. Container images are pinned to explicit tags, not
  `latest`, so a checkout from six months ago still brings up the same stack.
- **XII (correctness precedes performance)** — no performance work here, and
  none is warranted. Stated so nobody adds tuning to a feature that has no
  runtime path.
- **XIV (everything is traceable)** — this feature traces to `REQ-WP-001`
  through the spec's `traces:` field. Its tests will carry the trace marker and
  its source files the trace comment.

**Principles with no surface here, and why:** I and III (no look-ahead, immutable
history) govern feature computation and snapshots — this feature computes
nothing. II (time is not one thing) applies to models carrying timestamps; none
exist yet. IV, V (baselines before models, calibration) concern ML. VI (every
feature documented) concerns market features. VIII (connectors share one
interface) concerns connectors. IX (no automatic execution) concerns signals.
XIII (work is incremental) is satisfied by this being Phase 0's first slice.

**Gate result: PASS.** No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-project-bootstrap/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Version and image-tag decisions with their reasoning
├── quickstart.md        # The "one command" documentation SC-001 is measured against
└── tasks.md             # Created by /sdd-tasks, not by this step
```

**Deliberately not produced:**

- **`data-model.md`** — this feature introduces no domain entities. The spec's
  two "Key Entities" (development stack, environment file) are configuration,
  not data the system reasons about. The domain model is `REQ-WP-002`, and
  writing a placeholder here would invite someone to treat it as the real one.
- **`contracts/`** — nothing serves an API in this feature. Contracts arrive
  with the endpoints in `REQ-WP-009` and the API specification in PRD §28.

### Source Code (repository root)

Follows PRD §37's suggested layout, restricted to what this feature creates.
Directories the PRD names but this feature does not need are omitted rather than
created empty.

```text
market-forge/
├── pyproject.toml            # extended: product deps, mypy strict config
├── uv.lock                   # new: committed lockfile (Principle XI)
├── Makefile                  # extended: up, down, reset, typecheck targets
├── .env.example              # new: development-only defaults, committed
├── docker-compose.yml        # new: postgres + minio, health-gated, pinned tags
├── src/channelflow/
│   └── __init__.py           # new: the package strict typing applies to
├── apps/web/                 # new: Vite + React + TypeScript shell
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/{main.tsx,App.tsx}
└── tests/integration/
    └── test_dev_stack.py     # new: connects to each service, performs a real operation
```

**Structure Decision**: PRD §37's layout, adopted as far as this feature reaches.
`src/channelflow/` is created now because it is the tree strict typing is scoped
to and the domain model lands there next. `apps/web/` matches §37's `apps/web`.
`infra/` from §37 is **not** created — it holds per-service configuration
(§37 lists `infra/clickhouse`, `infra/postgres`, `infra/grafana`), and this
feature's services need no configuration files beyond environment variables.
`configs/`, `migrations/`, `research/` are likewise deferred to the features that
populate them.

The existing `tools/trace/` and `tests/tools/trace/` are untouched. They are
repository tooling, not product code, and remain outside the strict-typing scope
for the reason stated in Technical Context.

## Complexity Tracking

> Constitution Check passed with no violations. Nothing to justify.
