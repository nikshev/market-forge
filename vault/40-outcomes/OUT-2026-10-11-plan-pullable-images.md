---
id: OUT-2026-10-11-plan-pullable-images
step: plan
records: [REQ-INFRA-013]
commit: null
---

## What was done

Planned [[REQ-INFRA-013]] in `specs/144-pullable-images/`: `plan.md` and `tasks.md` (21 tasks; the first four
are the evidence already gathered, recorded rather than repeated).

## What was decided

- **One pin, written once as a compose anchor, with a test that CI names the same string.** Rejected: CI reading
  the compose file (a bigger change to a gate that cannot be run end to end locally) and generating one from the
  other.
- **The server image also runs the bucket one-shot**, because `mc` is in it (measured). One image fewer to vanish;
  rejected `pgsty/mc` as a second pin.
- **Tag plus index digest**, reversing for this image the choice ADR-064 made for the vendor's: the reason against
  a digest (it resolves through the same registry) still holds, but a third party's tag can be re-pushed.
- **`unknown` is a result, not a failure**, so that a Docker Hub 429 does not teach people to ignore the check.
- **The check is a developer tool under `tools/`**, a CI step and a `make` target, and not in the pre-commit hook
  (needs a network); REQ-INFRA-002's rule that no check be absent from both gates is met by CI.
- **The step cannot guard the job's `services:` images**, which are pulled before any step; it covers them by
  resolvability but cannot precede them. Said in the plan rather than implied away.
- **No change to the running stack.** Compose picks the new image only when a container is created.

## What is still open

- Whether anything else is red in CI: the later steps have not run since 2026-10-03. The plan is to read the
  whole run.
- Whether the live MinIO should later be moved onto the pinned image. Shown on a copy; not done.
