# Implementation Plan: Every pinned image can still be pulled, and a check says so first

**Branch**: `144-pullable-images` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/144-pullable-images/spec.md`

## Summary

Three small changes and one check. (1) The two MinIO image references in `docker-compose.yml` become one YAML
anchor naming `docker.io/pgsty/minio:RELEASE.2026-08-04T00-00-00Z@sha256:b6bfe723…2372`; the bucket one-shot
uses the same image (it contains `mc`) and the separate client image goes. (2) `ci.yml` names the same string,
and a test fails if the two differ. (3) `tools/images/` enumerates every image the compose file, the Dockerfiles
and the workflow name and asks each registry whether it resolves; CI runs it before its first pulling step and
`make images-resolvable` runs it locally. (4) An ADR records the trade.

## Technical Context

**Language/Version**: Python 3.12 (a developer tool under `tools/`, with the other dev tools).

**Primary Dependencies**: `pyyaml` (already a dependency); `docker` CLI for `manifest inspect` at run time only.
No new package.

**Testing**: pytest with no network for parsing and classification; the resolving itself is exercised by the CI
run. The registry call is behind a function the tests replace.

**Constraints**: the running containers are not recreated; the 12 object-store integration tests and the
byte-identical read of a copy of old data are the evidence for the swap and are already recorded in the spec.

**Scale/Scope**: seven registry images today (postgres, redpanda, prometheus, grafana, cloudflared, the MinIO
pair → one), four base images in two Dockerfiles, one workflow.

## Constitution Check

| Principle | Status |
|---|---|
| I–X | Not engaged: infrastructure only. |
| XI. Reproducible | **Engaged.** A checkout must resolve to the same stack later; a pin that cannot be pulled does not. Tag plus digest is stricter than before. |
| XII. Correctness before performance | N/A. |
| XIII. Incremental | One concern: where an image comes from. |
| XIV. Traceable | `# @trace: REQ-INFRA-013` in each new Python file; tests carry the marker. |

REQ-INFRA-002's rule ("no check may be absent from both gates") applies: the image check is a CI step and a
`make` target, and it is not in the pre-commit hook because it needs a network (the hook's contract).

## Project Structure

```text
tools/images/
├── __init__.py
├── enumerate.py     # images named by compose (all profiles), Dockerfiles, the workflow; variable defaults resolved
├── resolve.py       # `docker manifest inspect` -> served | gone | unknown (classification of the error text)
└── __main__.py      # `python -m tools.images`: the table, the exit code

tests/tools/images/
├── test_enumerate.py   # no network: each source, each edge case, the real repository's expected set
├── test_resolve.py     # classification of real error texts; the CLI's exit codes with a fake resolver
└── test_pin.py         # the repository's own files: one pin, tag + digest, compose == CI, no client image

tests/mutations/images_check.toml
vault/20-decisions/ADR-069.md
```

Touched: `docker-compose.yml` (anchor, `minio`, `minio_init`), `.github/workflows/ci.yml` (two images, one new
step), `Makefile` (`images-resolvable`), `vault/20-decisions/ADR-064.md` (status: superseded in part),
`docs/deployment.md` if it names the images.

**Structure Decision**: with the other developer tools in `tools/` (like `tools/notary/`), not in
`src/channelflow/`: it runs from a checkout or CI, never in the product.

## Design decisions, with what was rejected

1. **One pin, written once in the compose file as a YAML anchor, and checked equal in CI by a test.** Rejected:
   making CI read the compose file (a larger change to a gate that cannot be run end to end locally);
   generating one from the other (a build step for a string).
2. **The server image runs the bucket one-shot too.** `mc` is in it (measured: `mc --version`, `mc ready local`).
   The compose `entrypoint:` override already replaces the server's, as it replaced the client's. Rejected:
   `pgsty/mc` as a second pinned image (one more thing to vanish).
3. **Tag plus index digest.** The index digest covers every platform, so an arm64 reviewer pulls the same pin.
   [[ADR-064]] declined digests for the vendor's images because they resolve through the registry that may
   vanish; that is still true and no longer the point -- a third party's tag can be re-pushed, a vendor's less
   plausibly. Rejected: the tag alone; `latest` (the opposite of Principle XI).
4. **The release tested, not the newest.** `RELEASE.2026-08-04T00-00-00Z`, the one the 12 integration tests and
   the data copy ran on.
5. **`unknown` is its own outcome.** The check cannot tell "gone" from "rate-limited" by exit status alone, so the
   classification reads the error text (`unauthorized`, `denied`, `not found`, `manifest unknown`, `requires
   authentication` mean gone; `toomanyrequests`, `429`, `timeout`, `no such host`, `connection` mean unknown).
   Unknown does not fail the run: a check that fails on a Docker Hub hiccup is switched off the second time.
   The classification is data in `resolve.py`, with the real error texts seen on 2026-10-11 as test cases.
6. **Enumeration is parsing, not running.** Compose via YAML (anchors and `${VAR:-default}` resolved; services
   with `build:` skipped, they are tagged locally); Dockerfiles by `FROM` and `COPY --from` (stage names and
   `scratch` skipped); the workflow by YAML (`jobs.*.services.*.image`) plus `docker run` commands found in `run:`
   blocks (continuations joined, options that take a value skipped). A reference it cannot resolve to an image is
   *reported*, never silently dropped (spec edge case).
7. **The CI step goes after "Set up the environment" and before "Start the object store".** It needs Python
   (`pyyaml`), so it cannot be first; it precedes every pull that is a step. The job's `services:` images are
   pulled before any step -- they are covered by the check but cannot be guarded by it.
8. **No change to the running stack.** Compose only picks the new image when a container is created; the
   running `minio` and `minio_init` were created from the old ones and are left alone. The consequence is
   written in the ADR: the old image exists only in this host's cache.

## Risks

- **Provenance.** `pgsty/minio` is a community fork. Mitigations: development-only credentials, loopback-bound
  ports by default, a digest pin, a recorded test run and a recorded data comparison. Residual: it is not the
  vendor, and its maintenance is one group's decision. The check will announce the day it stops being served.
- **The first green CI run may fail somewhere else.** It has not run its later steps for eight days. The plan is
  to read the whole run, not to assume the MinIO step was the only problem; anything else found is recorded and,
  if it is not this change's to fix, named.
- **Anonymous Docker Hub reads from CI runners** are shared-IP and rate-limited. Handled by `unknown`.
- **A recreate of the live `minio` from the new image** is untested on the live data directory (shown on a
  copy). Not done here.

## Complexity Tracking

None.
