---
id: OUT-2026-10-11-implement-pullable-images
step: implement
records: [REQ-INFRA-013]
commit: null
---

## What was done

Implemented [[REQ-INFRA-013]] up to the point that needs a runner (tasks T005-T016 in
`specs/144-pullable-images/tasks.md`). Status is `tested`, not `implemented`: SC-002 -- the workflow's
object-store steps passing, and the steps after them running for the first time since 2026-10-03 -- can only be
earned by a CI run, which needs the push (T019-T021). The requirement moves to `implemented` in a later
commit that cites the run.

- **The check**: `tools/images/` (`enumerate.py`, `resolve.py`, `__main__.py`), `make images-resolvable`, and a
  CI step "Images are still served" before the first step that pulls.
- **The pin**: one compose anchor `x-minio-image`, shared by `minio` and `minio_init`, and the same string in the
  two `docker run` steps of `ci.yml`:
  `docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z@sha256:b6bfe7239bfc83fb90d31612d9704d86039dd714f7904b3f1ad68f211e602372`.
  The separate `mc` image is gone (`mc` is in the server image).
- **[[ADR-069]]** records the trade; [[ADR-064]] carries a note that its registry choice is superseded.
- **Mutation sweeps**: `images_enumerate.toml` (8/8 caught), `images_cli.toml` (4/4), `images_check.toml`
  (6 caught, 1 recorded survivor with a reason).

## Evidence

**RED first.** The new tests were run against the tree as committed at HEAD (compose and workflow still naming
`quay.io/minio/*`), in a throw-away export, before the configuration was edited:

    FAILED tests/tools/images/test_pin.py::test_the_server_and_the_bucket_one_shot_share_one_pinned_image
    FAILED tests/tools/images/test_pin.py::test_ci_names_the_identical_image_for_the_server_and_for_the_bucket
    FAILED tests/tools/images/test_pin.py::test_no_tracked_configuration_still_names_an_image_that_is_not_served
    3 failed, 38 passed

The 38 that pass there are the parsing and classification tests, whose subject (`tools/images`) was written
before this re-run; the order in which they first failed is the order the first run of this session recorded
(29 passed, 4 failed, the fourth being the real-repository enumeration, which then reported a locally built
image as unresolvable -- see below). Honest limit: the first-ever RED for the `tools/images` tests (module did
not exist yet) was not captured as text.

**GREEN.** After the edits: `tests/tools/images` 41 passed; `make lint` and `make typecheck` clean.

**The check, for real, against the registries (T013 / SC-001)**:

    served   cloudflare/cloudflared:2026.9.3
    served   docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z@sha256:b6bfe723...
    served   ghcr.io/astral-sh/uv:0.5.11
    served   grafana/grafana:12.2.0
    served   nginx:1.27-alpine
    served   node:22-alpine
    served   postgres:16-alpine3.24
    served   prom/prometheus:v3.6.0
    served   python:3.12-slim
    served   redpandadata/redpanda:v25.2.5
    10 image(s) named; 0 no longer served; 0 reference(s) could not be read.

Before the pin was changed the same command reported exactly the two `quay.io/minio/*` images as GONE.

**Compose** (T014): `docker compose config -q` passes with all profiles, and `config --images` lists the pinned
image for both `minio` and `minio_init`.

**The running stack was not touched** (T016 / SC-005): `docker inspect` start times of all 27 running containers,
recorded before the configuration edits and after, are identical.

**Recorded earlier in the session (T002, T003, SC-004)**: the 12 object-store integration tests pass against the
pinned image on throw-away ports; on a copy of the live data directory it lists 1,492 objects and the first
1,000 are byte-identical to what the running 2025 server returns.

## What was decided / found along the way

- **A first run of the check reported `channelflow-api:ci` as gone.** CI builds that image in the same job
  (`docker build -t`) and then `docker run`s it; asking a registry about it is a false alarm of exactly the kind
  that gets a check switched off. Images a job builds itself are now skipped, and a test pins it.
- **An `ARG` with no default, or a `FROM ${X}`, is reported `UNREAD` and fails the run**, never skipped: the
  alternative is a check that goes green while it cannot read the thing it exists to read.
- **`unknown` is checked before `gone`** in classification, and an unrecognised failure is `unknown`: a throttled
  reply that also mentions a denial must not read as the image being gone. A mutation (`unknown is checked after
  gone`) first survived; a mixed-text case in the tests now kills it.
- The recorded survivor in `images_check.toml` (dropping the `toomanyrequests` marker) is equivalent for every
  known text, because the fallback is already `unknown`; the reason is in the file.

## What is still open

- **CI has not run since 2026-10-03.** Whatever else is red behind the MinIO steps will only show after the push;
  the plan is to read the whole run (T020), not only the object-store steps.
- **The live MinIO still runs the 2025 image.** Moving it onto the pinned one is a deliberate separate step.
- **The check cannot guard a job's `services:` images** (pulled before any step); stated in the workflow.
