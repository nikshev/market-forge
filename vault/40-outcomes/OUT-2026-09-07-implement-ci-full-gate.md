---
id: OUT-2026-09-07-implement-ci-full-gate
step: implement
records: [REQ-INFRA-002]
commit: null
---

## What was done

All 12 tasks. The pre-commit hook now runs ruff and `make test-fast`
(`pytest -m "not integration"`) and needs no container runtime. The full gate —
lint, strict type check, the whole suite including integration tests, and
traceability coverage — runs in `.github/workflows/ci.yml` against provisioned
PostgreSQL and MinIO.

**Observed runs, not asserted ones:**

- Run `34135779903` — **failed**, before any check ran.
- Run `34135891226` — **passed**, 47s, all four checks green.
- Run `34136252630` — **failed on purpose**, verifying SC-004.

## What was decided

- **MinIO cannot be a GitHub Actions job service.** The first run failed at
  container initialisation: job services run a container's default entrypoint
  with no way to pass a command, and MinIO needs `server /data` — without it the
  image prints its usage text and exits. PostgreSQL is unaffected because it
  needs no command. MinIO now starts via `docker run` in a step, waiting for
  `/minio/health/live` rather than sleeping a guessed interval. **This was found
  by observing a real run**, which is exactly why T011 required observing one
  instead of trusting that the YAML looked right.
- **SC-004 verified adversarially.** I broke an integration test on a scratch
  branch and pushed it. The local fast gate passed it — correctly, the test is
  deselected there — and CI caught it, naming both the step ("Tests (including
  integration)") and the test (`test_postgres_answers_a_query - assert 1 == 999`).
  Branch deleted locally and on the remote. A negative case that is never run is
  a claim, not evidence.
- **FR-009 verified by comparing lists, not by asserting it.** `validate` left
  the hook and is present in the workflow; nothing is absent from both.

## What this surfaced about earlier work

- **`uv.lock` did not exist**, although FR-007 of REQ-WP-001 claims a committed
  lockfile, its task T003 was checked off, and the requirement stands at
  `implemented`. **I marked a task complete that I had not performed.** CI's
  cache annotation caught it — the local gate never could, because nothing
  checks that a claimed artifact exists. Fixed by generating it. Recorded here
  rather than quietly corrected, because a false completion is the precise
  failure this repository's review history has spent its time hunting.
- **The SDD toolchain was never declared.** Generating the lockfile and running
  `uv sync --frozen` deleted `specify` and `graphify` — both had been installed
  imperatively in earlier tasks and appear in no project file, so the entire
  pipeline's tooling was always one sync away from vanishing. That is a
  Principle XI failure that had been latent since Task 2. Both are now a
  `tooling` extra carried by the lockfile, and `make install` pulls them.

- **The two gates ran different ruff versions, and CI caught it.** The
  pre-commit config pinned `ruff-pre-commit` at `v0.6.9` while `make lint` used
  the project's ruff 0.16.6. They format the same file differently, so a commit
  passed the hook and failed CI — and would have ping-ponged forever, each gate
  undoing the other's formatting. Fixed by making the hook call `make lint`, so
  one ruff, pinned by `uv.lock`, serves both. This is the same principle the
  workflow already followed and the hook did not.
- **`make install` ignored the lockfile.** It ran `uv pip install -e`, which
  resolves afresh; `uv.lock` existed and was not consulted. Now `uv sync
  --frozen`. Without this the lockfile added an hour earlier was decorative,
  and CI and a developer's machine would drift onto different tool versions —
  exactly the divergence that produced the ruff conflict above.

## What is still open

- **No branch protection.** The workflow runs, but nothing requires it to pass
  before a merge to `main`. That is a repository setting, not a file, and it is
  the owner's to make. Until then CI reports rather than gates.
- **Two workflow annotations left unaddressed**: `actions/checkout@v4` and
  `astral-sh/setup-uv@v5` target a deprecated Node runtime, and the uv cache
  glob found no lockfile at the time (now fixed by the lockfile itself). Neither
  fails the run.
- **REQ-INFRA-002 has `VERIFIES` edges only from the local half**, by design.
  Setting `implemented` fired rule R2 — correctly, the requirement had no test
  at all — so four guards were written for the half that *is* testable, in
  `tests/tools/gates/test_two_gates.py`. Each was mutation-tested:
  pointing the workflow at `make test-fast` fails one, deleting `make validate`
  from the workflow fails another, and removing the integration marker fails a
  third. The first of those is the dangerous case: integration tests would then
  run in neither gate and everything would look green. FR-009 is now a
  regression guard rather than a comparison I did once by hand. The CI half
  remains evidenced by the three observed runs above, not by a test.
- **`make validate` still runs the full suite**, so running it locally needs the
  stack. That is unchanged and intended — it is the same command CI runs.
