---
traces: [REQ-INFRA-013]
status: draft
---

# Feature Specification: Every pinned image can still be pulled, and a check says so first

**Feature Branch**: `144-pullable-images`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-INFRA-013]] — operational finding 2026-10-11; follows [[ADR-064]]. Principle XI (a checkout resolves to the same stack later), [[REQ-INFRA-002]] (two gates; no check absent from both), Principle XIV.

## Context

A pin is a promise that a name will keep meaning the same bytes. [[ADR-064]] found out, on 2026-09-12, that a
promise made through a registry is only as durable as the registry: MinIO's images left Docker Hub, and the
fix then was to change the registry and keep the tags.

### Facts measured on 2026-10-11, not assumed

1. **Neither MinIO image is served any more.** `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z` and
   `quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z` cannot be pulled by an anonymous client: quay's API answers
   `Requires authentication` for the repository, `docker manifest inspect` fails for the pinned tags and for
   `latest`, Docker Hub's `minio/minio` still answers `object not found`. The running stack holds both only
   because they were pulled earlier.
2. **CI has been red since 2026-10-03** at "Start the object store" with `docker: unauthorized: access to the
   requested resource is not authorized`. Nothing after that step has run, so the lint, the type check, the
   full test run, the front-end checks and the traceability coverage that the pre-commit hook defers to CI
   (CLAUDE.md, "Two gates") have not been enforced anywhere.
3. **A stranger cannot start the stack.** The README's quick start ends in `docker compose up`; on a machine
   without a cached copy it fails at the same pull. For the repository's reviewers that is every machine.
4. **There are pullable replacements.** `pgsty/minio` (a community-maintained fork, "SILO") is served from
   Docker Hub with versioned tags, as is `pgsty/mc`; so are `bitnamilegacy/minio` (frozen), a Chainguard build
   (`latest` only) and `rustfs/rustfs` (a different server). Of these only the fork is a drop-in: the same
   `server /data` command, the same environment variables, and **`mc` inside the server image** (`mc ready
   local`, the compose healthcheck, works unchanged).
5. **It works here.** The integration tests that need an object store (12) pass against
   `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` on throw-away ports; started on a copy of the live data directory
   the same build lists 1,492 objects and returns the first 1,000 byte-identical to what the running 2025
   server returns.
6. **The images the stack names today:** `postgres:16-alpine3.24`, `redpandadata/redpanda:v25.2.5`,
   `prom/prometheus:v3.6.0`, `grafana/grafana:12.2.0` (all on Docker Hub, resolvable), the two MinIO images
   above, and the base images in the Dockerfiles. Only the MinIO pair is unresolvable.

### What this is not

It does not replace MinIO's role, move the running stack's storage onto the new image, mirror or vendor images,
or touch any image that still resolves. The running containers are not recreated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A stranger can bring the object store up (Priority: P1)

Someone who clones the repository on a machine with no cached images runs the documented start-up and gets a
working object store with its bucket.

**Why this priority**: it is the first command a reviewer runs.

**Independent Test**: on a clean Docker host (no cached copy), pull exactly the images the compose file names
for the object store and its bucket step and start them; the health check passes and the bucket exists.

**Acceptance Scenarios**:

1. **Given** the images named by `docker-compose.yml` for the object store and the bucket step, **When** an
   anonymous client resolves them, **Then** every one resolves.
2. **Given** the pinned server image, **When** it is started as compose starts it, **Then** `mc ready local`
   succeeds and the bucket-creation step creates the configured bucket and exits 0.
3. **Given** the pin, **When** it is read, **Then** it carries a release tag **and** an index digest.

---

### User Story 2 - CI runs its gate again (Priority: P1)

The object-store steps of the workflow pull a resolvable image and the rest of the gate runs.

**Independent Test**: the workflow and the compose file name the same server image; after the push, the
"Start the object store" and "Create the object store bucket" steps pass on a runner.

**Acceptance Scenarios**:

1. **Given** `ci.yml` and `docker-compose.yml`, **When** their object-store images are compared, **Then** they are
   identical strings (they cannot drift).
2. **Given** the workflow, **When** it runs on `main`, **Then** both object-store steps succeed (evidence: the
   run, cited in the outcome note).

---

### User Story 3 - The next vanishing is announced, early and by name (Priority: P1)

A check asks every registry whether every image the repository names still resolves, and CI runs it before its
first pull.

**Why this priority**: this is the second time. The first fix repaired one registry entry; the lesson is that
the failure should be cheap to see.

**Independent Test**: parsing is tested with no network (images found in the compose file, the Dockerfiles and
the workflow; variable defaults resolved; digests and tags separated; locally built images skipped); the
resolving step is exercised by the CI run.

**Acceptance Scenarios**:

1. **Given** the repository, **When** the check enumerates images, **Then** it finds every image in the compose
   file (all profiles), the `FROM` and `COPY --from` references in the Dockerfiles, and every `docker run` image
   and service image in the workflow, and skips the images the compose file builds itself.
2. **Given** an image that does not resolve, **When** the check runs, **Then** it exits non-zero and names the
   image and where it is referenced, and says that the registry no longer serves it.
3. **Given** a registry that is rate-limiting or unreachable, **When** the check runs, **Then** that image is
   reported as **unknown**, not as gone, and does not fail the run by itself (a false alarm would teach people
   to ignore the check).
4. **Given** the workflow, **When** it runs, **Then** the check runs before the first step that pulls.

---

### User Story 4 - The replacement is not a leap of faith (Priority: P2)

The replacement was shown to read data the previous release wrote, and the running stack was not touched.

**Independent Test**: the recorded integration run and the recorded comparison on a copy; `docker inspect` of
the running containers before and after shows unchanged start times.

**Acceptance Scenarios**:

1. **Given** the 12 object-store integration tests, **When** they run against the pinned image, **Then** they pass.
2. **Given** a copy of data written by the previous release, **When** the pinned image serves it, **Then** its
   objects list and read back byte-identical.
3. **Given** this change committed, **When** the running containers are inspected, **Then** none was recreated.

---

### User Story 5 - The trade is written down (Priority: P2)

An ADR records why a community fork replaced the vendor image, what that costs, and what would change the choice.

**Acceptance Scenarios**:

1. **Given** the ADR, **When** it is read, **Then** it names the provenance change, the mitigation (tag + digest,
   development-only credentials, the integration run, the data comparison), the residual risk, and the exit.

### Edge Cases

- **The fork's tag is re-pushed:** the digest pin refuses it (this is why a digest, which ADR-064 declined for the
  vendor's own images, is right for a third party's).
- **Docker Hub's anonymous pull limit:** `manifest inspect` is a registry read and counts; the check must treat a
  429 or a network failure as *unknown*.
- **A reviewer on arm64:** the pin is the *index* digest, which covers both platforms.
- **The previous release's data under the new image on the live stack:** shown to read on a copy; replacing the
  running image in place is a separate, deliberate step, not part of this change.
- **The fork stops being maintained:** the exit is the same as today's -- another S3-compatible server -- and the
  check is what will announce it.
- **An image referenced through a variable with no default:** reported as unresolved-by-the-check, never silently
  skipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The object store server and its bucket-creation one-shot MUST use an image an anonymous client can
  pull, pinned to a release tag and the image's index digest. If the server image contains `mc`, the separate
  client image MUST be dropped.
- **FR-002**: `docker-compose.yml` and `ci.yml` MUST name the identical object-store image, and a test MUST fail
  if they differ.
- **FR-003**: The compose health check and the bucket step MUST keep working unchanged in behaviour (`mc ready
  local`; the configured bucket exists after start).
- **FR-004**: A check MUST enumerate the images named by the compose file (all profiles), the Dockerfiles and the
  workflow, skipping images the compose file builds, and ask each registry whether each resolves.
- **FR-005**: The check MUST exit non-zero for an image that is not served, naming it and its references; it MUST
  report a rate-limited or unreachable registry as *unknown* and not fail on that alone.
- **FR-006**: The workflow MUST run the check before its first pulling step, and `make` MUST expose it so a
  developer runs the same thing.
- **FR-007**: The enumeration MUST be testable without a network.
- **FR-008**: The integration tests that need the object store MUST pass against the pinned image, and the pinned
  image MUST be shown to list and read byte-identical objects from a copy of data written by the previous release;
  both are recorded.
- **FR-009**: An ADR MUST record the decision and supersede [[ADR-064]]'s registry choice.
- **FR-010**: The change MUST NOT recreate the running containers.
- **FR-011**: Every file added carries a requirement trace (Principle XIV).

### Key Entities

- **Image reference**: repository, tag, optional digest, and where it appears (file and line).
- **Resolution result**: `served`, `gone` (registry says unknown/denied), or `unknown` (rate limit, network).
- **Pin**: tag plus index digest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The check run against the repository reports zero images gone: every image it enumerates resolves.
- **SC-002**: After the push, the workflow's "Start the object store" and "Create the object store bucket"
  steps succeed, and the steps after them run (they have not run since 2026-10-03).
- **SC-003**: The check's enumeration finds at least the six registry images the compose file names and the
  workflow's own, and its parsing is covered by tests that run with no network.
- **SC-004**: The 12 object-store integration tests pass against the pinned image; the copy comparison reads
  1,000 of 1,000 objects byte-identical.
- **SC-005**: The start times of every running container are the same before and after the change.

## Assumptions

- The community fork is an acceptable replacement for a development and demonstration stack whose credentials
  are development-only (`channelflow_dev_only`) and whose ports bind to loopback by default; for anything holding
  real value it would need the review a vendor image gets. This is stated in the ADR, not assumed away.
- The release chosen is the one the evidence was gathered on (`RELEASE.2026-08-04T00-00-00Z`), not the newest
  (`2026-09-16`): a pin should be what was tested.
- Anonymous reads of Docker Hub from a CI runner succeed far more often than they are rate-limited; the *unknown*
  outcome exists for the days they are not.
- The README's quick start is not otherwise changed here; whether it should mention the fork is for the ADR to say.
