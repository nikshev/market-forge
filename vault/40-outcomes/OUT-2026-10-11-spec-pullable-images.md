---
id: OUT-2026-10-11-spec-pullable-images
step: spec
records: [REQ-INFRA-013]
commit: null
---

## What was done

Wrote [[REQ-INFRA-013]] and specified it as `specs/144-pullable-images/spec.md`. The scope is set by six facts
measured the same day: neither MinIO image is served any more (the second time, after [[ADR-064]]); CI has been red
since 2026-10-03 at the first pull, so the gate it carries has not run; `docker compose up` per the README fails
on any machine without a cached copy; a drop-in replacement exists (`pgsty/minio`, which also contains `mc`); it
passes the object-store integration tests; and it reads a copy of the previous release's data byte-identically.

## What was decided

- **Not just a tag change.** ADR-064's answer (change the registry, keep the tags) has now failed once; repeating it
  would be the same bet. The spec adds a check that makes the next failure cheap to see, and moves the pin to tag
  **plus index digest**.
- **A digest this time, which ADR-064 declined for the vendor's own images.** The reason against was that a digest
  is resolved through the same registry and fails the same way when the repository is gone. That is still true,
  but it is no longer the question: the new image is a third party's, and a re-pushed tag from a fork is a risk a
  vendor's was not. Both facts are stated rather than one chosen silently.
- **The server image replaces the client image too.** It contains `mc`, so the one-shot that creates the bucket
  uses it and one dependency disappears.
- **Rate limits are "unknown", not "gone".** A check that cries wolf on a Docker Hub 429 would be ignored by the
  day it is right.
- **The running stack is out of scope.** The new build was shown to read a copy of the live data; replacing the
  running image is a separate decision, because it is a restart of the object store under a live pipeline.
- **The release is the one tested (2026-08-04), not the newest (2026-09-16).**

## What is still open

- **Provenance.** A community fork replaces the vendor's image; the ADR must say what that does and does not
  change for a stack whose credentials are development-only and whose ports bind to loopback.
- **Whether the live MinIO should be moved onto the pinned image.** Not decided here. Until it is, a recreate of
  that container from the *old* image is impossible on a machine without the cache -- the running one included.
- **What else the CI gate will find** once it runs again: it has been dark for eight days.
