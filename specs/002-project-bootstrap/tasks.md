---
description: "Task list for REQ-WP-001 project bootstrap"
---

# Tasks: Project Bootstrap

**Input**: Design documents from `/specs/002-project-bootstrap/`

**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Included. The spec's SC-002 requires the stack be verified by
connecting to each service and performing a real operation, and this repository
gates on traceability — every test carries `@pytest.mark.trace("REQ-WP-001")`.

**Organization**: Grouped by the spec's three user stories so each can be
implemented and verified on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: which user story the task serves

---

## Phase 1: Setup

**Purpose**: the Python package and its tooling configuration.

- [ ] T001 Create `src/channelflow/__init__.py` with a module docstring and the `# @trace: REQ-WP-001` marker. This is the only Python source this feature produces — see Notes on sparse code links.
- [ ] T002 Extend `pyproject.toml`: add a `[tool.mypy]` section configured strict over `src`, and declare the product package under `[tool.setuptools.packages.find]` alongside the existing `tools*`. Confirm `requires-python` still pins 3.12 (FR-007).
- [ ] T003 Generate and commit `uv.lock` (FR-007, Principle XI — a checkout must resolve to the same versions later).

---

## Phase 2: Foundational

**Purpose**: configuration both the stack and the tests read. Blocks US1.

- [ ] T004 Create `.env.example` declaring `POSTGRES_*` and `MINIO_*` credentials, ports and bucket name, with development-only defaults (FR-006).
- [ ] T005 Add `.env` to `.gitignore` so real credentials cannot be committed (FR-006).

**Checkpoint**: configuration exists; US1 can begin.

---

## Phase 3: User Story 1 — Start the dev stack with one command (P1) 🎯 MVP

**Goal**: `make up` brings up PostgreSQL and MinIO, health-gated, and the services answer real requests.

**Independent Test**: from a clean checkout with nothing running, `make up` then the integration tests pass.

### Tests for User Story 1

> Write these FIRST and confirm they FAIL — with no compose file there is nothing to connect to, which is the right reason to fail.

- [ ] T006 [P] [US1] `tests/integration/test_dev_stack.py::test_postgres_answers_a_query` — connect using the values from `.env` and execute `SELECT 1`. Marker: `@pytest.mark.trace("REQ-WP-001")`.
- [ ] T007 [P] [US1] `tests/integration/test_dev_stack.py::test_object_store_lists_buckets` — connect to MinIO over the S3 API and list buckets. Marker as above.

### Implementation for User Story 1

- [ ] T008 [US1] Create `docker-compose.yml` with two services: PostgreSQL 16 and MinIO, both pinned to explicit tags (never `latest`, per research.md), both declaring a health condition, both reading ports and credentials from `.env`, both with a named volume (FR-002, FR-003, FR-006).
- [ ] T009 [US1] Add `up`, `down` and `reset` targets to the `Makefile`. `up` waits for health before returning success; `down` preserves volumes; `reset` removes them and is the only destructive command (FR-001, FR-003, FR-005).
- [ ] T010 [US1] Verify FR-004 and SC-004 by hand: run `make up` twice in succession and confirm the second run succeeds and leaves the same end state as one run. Record the observed output in the implement-step outcome note.
- [ ] T011 [US1] Verify SC-005 by hand: write a row to PostgreSQL, `make down`, `make up`, confirm the row survives. Then confirm `make reset` discards it.

**Checkpoint**: US1 complete — the acceptance criterion of REQ-WP-001 holds.

---

## Phase 4: User Story 2 — Quality gate green on a clean checkout (P2)

**Goal**: lint, strict type check and tests all pass with no findings.

**Independent Test**: run the three commands on a clean checkout; all pass.

- [ ] T012 [US2] Add a `typecheck` target to the `Makefile` running `mypy --strict` over `src` (FR-008, FR-009).
- [ ] T013 [US2] Run `make lint`, `make typecheck` and `make test` and confirm all three are green with no warnings in output (FR-011, SC-003). Fix whatever is not.

**Checkpoint**: US2 complete — a red result from here on is a real change, not the environment.

---

## Phase 5: User Story 3 — Web application shell builds (P3)

**Goal**: a Vite/React/TypeScript shell that builds and type-checks, with no charting library.

**Independent Test**: install dependencies, build, type-check — all succeed.

- [ ] T014 [US3] Scaffold `apps/web/` with Vite, React 18 and TypeScript: `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `src/main.tsx`, `src/App.tsx` rendering one empty page. No Lightweight Charts — that is REQ-WP-009 (FR-010).
- [ ] T015 [US3] Add `apps/web/node_modules` and `apps/web/dist` to `.gitignore`.
- [ ] T016 [US3] Run the frontend build and type-check and confirm both succeed (SC-006).

**Checkpoint**: US3 complete — toolchain and versions fixed before any interface is designed.

---

## Phase 6: Polish

- [ ] T017 Walk `quickstart.md` end to end from a clean state and correct anything that does not match reality (FR-012, SC-001).
- [ ] T018 Add the new `make` targets (`up`, `down`, `reset`, `typecheck`) to `CLAUDE.md`'s commands section so they are discoverable from the repository's own documentation, not only from this spec (FR-012).

---

## Dependencies & Execution Order

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: after Setup. Blocks US1 — the compose file and the integration tests both read `.env`.
- **US1 (Phase 3)**: after Foundational. This is the MVP; REQ-WP-001's stated acceptance criterion is satisfied at its checkpoint.
- **US2 (Phase 4)**: after Setup. Independent of US1 — the quality gate does not need running services. Could run in parallel with US1 if staffed.
- **US3 (Phase 5)**: after Setup. Independent of both US1 and US2.
- **Polish (Phase 6)**: after all three stories.

### Parallel opportunities

- T006 and T007 are marked [P]: different test functions, no shared state.
- US2 and US3 are independent of US1 and of each other.
- Everything within Phase 1 is sequential — T002 and T003 both touch dependency resolution.

---

## Notes

**On sparse code links.** This feature produces almost no Python: its output is
a compose file, a Makefile, an env example and a frontend scaffold. Only
`src/channelflow/__init__.py` can carry a `# @trace:` comment, because the
collector scans `.py`, `.ts`, `.tsx`, `.js` and `.jsx` under `src/` and `tools/`
and ignores everything else. So the `IMPLEMENTS` edge for REQ-WP-001 will be a
single thin link.

That is honest rather than manufactured. `CLAUDE.md` already records that code
links are advisory — no validator rule requires an `IMPLEMENTS` edge — and
inventing a Python file to carry a marker would be exactly the token gesture
this repository's review history has spent its time removing. The `VERIFIES`
edges from T006 and T007 are the real evidence that this feature works.

**On manual verification tasks.** T010, T011, T013, T016 and T017 are checks a
person runs, not automated tests. They are listed as tasks because the spec
states them as success criteria and an unlisted check is an unrun one. Their
results belong in the implement-step outcome note.
