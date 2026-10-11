---
id: REQ-INFRA-013
title: "Every container image the stack and CI pull can still be pulled, and a check says so before anything pulls"
type: infrastructure
prd_ref: "none -- operational finding, 2026-10-11; repository practice (ADR-064, REQ-INFRA-002)"
prd_lines: "0-0"
phase: null
status: implemented
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
- **Tests:**
    - `tests/tools/images/test_enumerate.py::test_a_reference_is_split_into_name_tag_and_digest[docker.io/pgsty/minio:RELEASE.X@sha256:abababababababababababababababababababababababababababababababab-docker.io/pgsty/minio-RELEASE.X-sha256:abababababababababababababababababababababababababababababababab]`
    - `tests/tools/images/test_enumerate.py::test_a_reference_is_split_into_name_tag_and_digest[ghcr.io/astral-sh/uv@sha256:cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd-ghcr.io/astral-sh/uv-None-sha256:cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd]`
    - `tests/tools/images/test_enumerate.py::test_a_reference_is_split_into_name_tag_and_digest[localhost:5000/team/img:1.2-localhost:5000/team/img-1.2-None]`
    - `tests/tools/images/test_enumerate.py::test_a_reference_is_split_into_name_tag_and_digest[postgres-postgres-None-None]`
    - `tests/tools/images/test_enumerate.py::test_a_reference_is_split_into_name_tag_and_digest[postgres:16-alpine3.24-postgres-16-alpine3.24-None]`
    - `tests/tools/images/test_enumerate.py::test_a_reference_is_split_into_name_tag_and_digest[quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z-quay.io/minio/minio-RELEASE.2025-09-07T16-13-09Z-None]`
    - `tests/tools/images/test_enumerate.py::test_compose_images_are_found_in_every_profile_with_defaults_resolved_and_built_images_skipped`
    - `tests/tools/images/test_enumerate.py::test_dockerfile_from_and_copy_from_are_found_and_stage_names_are_not_images`
    - `tests/tools/images/test_enumerate.py::test_the_real_repository_names_the_registry_images_it_is_known_to_use`
    - `tests/tools/images/test_enumerate.py::test_the_workflow_services_and_multi_line_docker_run_commands_are_found`
    - `tests/tools/images/test_pin.py::test_ci_names_the_identical_image_for_the_server_and_for_the_bucket`
    - `tests/tools/images/test_pin.py::test_no_tracked_configuration_still_names_an_image_that_is_not_served`
    - `tests/tools/images/test_pin.py::test_the_health_check_and_the_bucket_step_still_use_mc`
    - `tests/tools/images/test_pin.py::test_the_server_and_the_bucket_one_shot_share_one_pinned_image`
    - `tests/tools/images/test_resolve.py::test_a_docker_that_hangs_or_is_missing_is_unknown_never_gone`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[429 Too Many Requests: unauthorized: authentication required]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[Error response from daemon: Head "https://registry-1.docker.io/v2/x/manifests/1": net/http: TLS handshake timeout]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[Get "https://quay.io/v2/": dial tcp 1.2.3.4:443: connect: connection refused]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[Temporary failure in name resolution]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[You have reached your pull limit; the rate limit resets in six hours]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[dial tcp: lookup registry-1.docker.io: no such host]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[i/o timeout]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[net/http: request canceled (Client.Timeout exceeded while awaiting headers) timed out]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[received unexpected HTTP status: 429 Too Many Requests]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[toomanyrequests: You have reached your pull rate limit.]`
    - `tests/tools/images/test_resolve.py::test_a_rate_limit_or_a_network_failure_is_unknown_never_gone[toomanyrequests: retry later]`
    - `tests/tools/images/test_resolve.py::test_an_image_the_check_cannot_read_fails_the_run_instead_of_vanishing`
    - `tests/tools/images/test_resolve.py::test_each_distinct_reference_is_asked_about_once`
    - `tests/tools/images/test_resolve.py::test_success_is_served_and_an_unrecognised_failure_is_unknown_not_gone`
    - `tests/tools/images/test_resolve.py::test_the_command_exits_one_naming_the_image_and_where_it_is_referenced`
    - `tests/tools/images/test_resolve.py::test_the_command_exits_zero_when_everything_is_served_or_merely_unknown`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[Error response from daemon: manifest for acme/x:9 not found: manifest unknown: manifest unknown]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[Error response from daemon: pull access denied for minio/minio, repository does not exist or may require 'docker login']`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[Requires authentication]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[authentication required]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[denied: requested access to the resource is denied]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[docker: Error response from daemon: unauthorized: access to the requested resource is not authorized]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[manifest unknown: manifest unknown]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[name unknown: repository name not known to registry]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[no such manifest: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z]`
    - `tests/tools/images/test_resolve.py::test_the_registry_saying_it_does_not_have_the_image_is_gone[unauthorized: authentication required]`
- **Code:**
    - `tools/images/__main__.py`
    - `tools/images/enumerate.py`
    - `tools/images/resolve.py`
- **Outcomes:** [[OUT-2026-10-11-implement-pullable-images]], [[OUT-2026-10-11-plan-pullable-images]], [[OUT-2026-10-11-spec-pullable-images]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

- Found while answering "what is left before the hackathon submission": the last CI run on `main` is red since
  2026-10-03, and the cause (an image that cannot be pulled) is not specific to CI.
- Verified on 2026-10-11 before this note was written: `pgsty/minio` and `pgsty/mc` ("SILO", a community-maintained
  fork of MinIO) are pullable and versioned; the integration tests that touch the object store passed against
  `RELEASE.2026-08-04T00-00-00Z` on throw-away ports; the same build started on a copy of the live data
  directory listed 1,492 objects and returned the first 1,000 byte-identical to the running old server.
