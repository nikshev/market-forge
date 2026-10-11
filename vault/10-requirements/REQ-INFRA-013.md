---
id: REQ-INFRA-013
title: "Every container image the stack and CI pull can still be pulled, and a check says so before anything pulls"
type: infrastructure
prd_ref: "none -- operational finding, 2026-10-11; repository practice (ADR-064, REQ-INFRA-002)"
prd_lines: "0-0"
phase: null
status: specified
depends_on: [REQ-INFRA-002]
tags: [ci, images, reproducibility, supply-chain]
hard_gated: false
---

## Requirement

`docker-compose.yml`, the `Dockerfile`s and `.github/workflows/ci.yml` pull container images by a pinned tag,
because Principle XI wants a checkout to resolve to the same stack later. [[ADR-064]] recorded the first time a
pin outlived its registry (MinIO left Docker Hub; the pins moved to `quay.io`, same tags). **It has happened
again, and this time there was nowhere to move to:** an anonymous client can no longer pull
`quay.io/minio/minio` or `quay.io/minio/mc` (quay answers `Requires authentication` for the repository, Docker
Hub answers `object not found`), so

* CI fails at "Start the object store" (`unauthorized: access to the requested resource is not authorized`) and
  has not run its gate since;
* `docker compose up` per the README fails on **any machine without a cached copy** -- which is every reviewer's
  machine. The running stack on the development host works only because the images were pulled earlier.

Both images must come from somewhere a stranger can pull today, and the next vanishing must be announced by a
check that says which image is gone, not discovered as a `docker run` error halfway through a CI job.

## Acceptance

- The object store server and the bucket-creation one-shot use images an **anonymous client can pull now**,
  pinned to a release tag **and its index digest** (a third-party build warrants more than a tag). If the server
  image already contains `mc`, the separate client image is dropped.
- `docker-compose.yml` and `ci.yml` name the same image, so the two cannot drift.
- The integration tests that need the object store pass against the new image (a recorded run), and the new image,
  started on a **copy** of data written by the previous release, lists and returns byte-identical objects (a
  recorded comparison). Upgrading the running stack's storage in place is **not** part of this requirement.
- A check lists every image named by the compose file (all profiles), the Dockerfiles and the CI workflow, and
  asks each registry whether it resolves. It runs in CI **before** the first pull. Its parsing is tested with no
  network.
- An ADR records the choice, supersedes [[ADR-064]]'s "change the registry, keep the tags", names the provenance
  trade-off (a community fork replaces the vendor's image) and the residual risk.
- CI runs the object-store steps green on `main` after the push (the run is cited in the outcome note).
- The running containers are not recreated by this change.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-144-pullable-images]]
- **Outcomes:** [[OUT-2026-10-11-spec-pullable-images]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

- Found while answering "what is left before the hackathon submission": the last CI run on `main` is red since
  2026-10-03, and the cause (an image that cannot be pulled) is not specific to CI.
- Verified on 2026-10-11 before this note was written: `pgsty/minio` and `pgsty/mc` ("SILO", a community-maintained
  fork of MinIO) are pullable and versioned; the integration tests that touch the object store passed against
  `RELEASE.2026-08-04T00-00-00Z` on throw-away ports; the same build started on a copy of the live data
  directory listed 1,492 objects and returned the first 1,000 byte-identical to the running old server.
