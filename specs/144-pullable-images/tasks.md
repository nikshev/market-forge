---
description: "Tasks for REQ-INFRA-013 -- every pinned image can still be pulled, and a check says so first"
---

# Tasks: Every pinned image can still be pulled, and a check says so first

**Input**: `spec.md`, `plan.md`. Tests first; the RED output goes into the implementation outcome note.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Evidence already gathered (recorded, not redone)

- [X] T001 Registry state, 2026-10-11: the MinIO pair unresolvable, the other images resolvable; `pgsty/minio` and its `mc` pullable
- [X] T002 12 object-store integration tests pass against `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` on throw-away ports
- [X] T003 The same build on a copy of the live data: 1,492 objects listed, first 1,000 byte-identical to the running 2025 server
- [X] T004 Record `docker inspect` start times of every running container (SC-005 baseline)

## Phase 2: The check

- [X] T005 [P] [US3] `tests/tools/images/test_enumerate.py` (no network): compose images including a profile-gated one and a `${VAR:-default}`; an anchor; a `build:` service skipped; Dockerfile `FROM`/`COPY --from` with stage names, `scratch` and an `ARG`-based `FROM` (reported as unresolved, not dropped); the workflow's `services:` image and a multi-line `docker run` with `-p`/`-e`/`--entrypoint` options; tag and digest separated; and the **real repository's** set contains at least the six registry images and the base images
- [X] T006 [P] [US3] `tests/tools/images/test_resolve.py`: the real error texts seen on 2026-10-11 classify as `gone` (`unauthorized: access to the requested resource is not authorized`, `pull access denied ... repository does not exist`, `manifest unknown`, `no such manifest`); `toomanyrequests`, `429`, `i/o timeout`, `no such host`, `connection refused` classify as `unknown`; success is `served`; the CLI exits 1 for a gone image and names it and its references, 0 when only unknown
- [X] T007 [US3] `tools/images/{__init__,enumerate,resolve,__main__}.py` (`# @trace: REQ-INFRA-013`)
- [X] T008 [P] `tests/mutations/images_check.toml`: break the stage-name skip, the build-service skip, the gone/unknown classification, the exit code; each caught or a survivor with a reason

## Phase 3: The pin

- [X] T009 [P] [US1] [US2] `tests/tools/images/test_pin.py` on the repository's own files: exactly one object-store image in compose, shared by `minio` and `minio_init`; it carries a release tag **and** a `sha256` digest; `ci.yml` names the identical string; no reference to `quay.io/minio` remains anywhere tracked outside vault/specs history; `minio_init` no longer names a separate client image
- [X] T010 [US1] [US2] `docker-compose.yml`: the anchor, `minio`, `minio_init`; `.github/workflows/ci.yml`: the two `docker run` images
- [X] T011 [US3] `Makefile`: `images-resolvable`; `ci.yml`: the step "Images are still served" after "Set up the environment" and before "Start the object store"
- [X] T012 [US5] `vault/20-decisions/ADR-069.md`; mark `ADR-064` as superseded in part; `docs/deployment.md` if it names the images

## Phase 4: Gate and evidence

- [X] T013 Run the check for real: `python -m tools.images` against the repository and the registries; zero gone
- [X] T014 `docker compose config -q` (all profiles) and `docker compose --profile telegram --profile notary config --images` list the new image once
- [ ] T015 Run the full gate: `make lint`, `make typecheck`, `make graph` once; `status: tested`; commit with explicit paths
- [X] T016 SC-005: the start times of every running container, after, equal the baseline of T004

## Phase 5: Land and prove in CI

- [ ] T017 Before pushing: scan what will be published (`git log origin/main..main`) for key-shaped values next to key words, and the actual deploy key's value; `.env` untracked
- [ ] T018 Add `LICENSE` (MIT) and the README licence section (separate, trivial commit; asked for alongside this work)
- [ ] T019 Push `main` (authorised by the owner on 2026-10-11)
- [ ] T020 Watch the CI run to the end; read the whole log, not only the MinIO steps; record anything else it finds
- [ ] T021 `status: implemented` with the run cited in the outcome note; commit with explicit paths

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 pullable, tag + digest, client image dropped | T001, T009, T010 |
| FR-002 compose == CI, test | T009 |
| FR-003 health check and bucket step unchanged in behaviour | T002, T010, T014 |
| FR-004 enumeration | T005, T007 |
| FR-005 gone vs unknown | T006, T007 |
| FR-006 CI step before the first pull; `make` target | T011 |
| FR-007 enumeration testable offline | T005 |
| FR-008 integration + data copy recorded | T002, T003 |
| FR-009 ADR | T012 |
| FR-010 running stack untouched | T004, T016 |
| FR-011 traceability | every new Python file and test |
| SC-001 zero gone | T013 |
| SC-002 CI object-store steps green, later steps run | T020, T021 |
| SC-003 enumeration finds the registry images, offline tests | T005 |
| SC-004 12 tests, 1,000/1,000 | T002, T003 |
| SC-005 start times | T004, T016 |
