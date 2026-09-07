# Implementation Plan: CI runs the full gate

**Branch**: `003-ci-full-gate` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

## Summary

Split one gate into two. A GitHub Actions workflow provisions PostgreSQL and
MinIO and runs lint, strict type check, the full suite and traceability
coverage. The local pre-commit hook keeps lint, formatting and the
non-integration tests, and stops needing a container runtime.

## Technical Context

**Language/Version**: YAML for the workflow; the checks themselves are the
existing `make` targets, unchanged.

**Primary Dependencies**: GitHub Actions with job `services:` for PostgreSQL and
MinIO. `uv` for the Python environment, as locally. No new Python dependency.

**Storage**: none of its own. The workflow's services are ephemeral.

**Testing**: the workflow *is* the test of this feature. Its acceptance is
observed from a real run, not from a unit test — see Constitution Check.

**Target Platform**: `ubuntu-latest`.

**Project Type**: repository tooling.

**Performance Goals**: none stated. Worth watching: the workflow runs the whole
suite, and if it grows slow enough to be ignored it has failed differently.

**Constraints**: FR-009 — no check may be absent from both gates. That is the
one property whose violation would make this feature harmful rather than merely
incomplete.

**Scale/Scope**: one workflow file, one pre-commit config change, one pytest
marker, documentation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Binding here:

- **XI (results are reproducible)** — the workflow pins action versions and
  service image tags exactly as `docker-compose.yml` does, for the same reason.
- **XII (correctness precedes performance)** — the workflow runs everything
  rather than a fast subset. If that becomes slow, the answer is faster checks,
  not fewer.
- **XIV (everything is traceable)** — this feature has a requirement,
  `REQ-INFRA-002`, written before the work.

**A gap this feature cannot close, stated rather than hidden**: its own
acceptance is a workflow run, and a workflow run cannot be asserted by a test in
the suite it gates. There is no honest way to give `REQ-INFRA-002` a `VERIFIES`
edge from a unit test that proves CI works. What *can* be tested is the local
half — that the fast gate still rejects what it should. The workflow half is
verified by observing a real run and recording it. This is the same class of
limit `CLAUDE.md` already documents for self-asserted markers, and it is
recorded here rather than papered over with a test that asserts a YAML file
parses.

**Gate result: PASS**, with that limit noted. Complexity Tracking empty.

## Project Structure

```text
.github/workflows/ci.yml      # new: the full gate
.pre-commit-config.yaml       # modified: fast gate only
pyproject.toml                # modified: register the `integration` marker
Makefile                      # modified: `test-fast` target
tests/integration/            # modified: mark the two existing tests
CLAUDE.md                     # modified: document the two gates
```

**Structure Decision**: the workflow calls the same `make` targets a developer
runs. Nothing in CI reimplements a check, so the two cannot drift.

## Complexity Tracking

> No violations.
