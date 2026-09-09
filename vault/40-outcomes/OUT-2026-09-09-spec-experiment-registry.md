---
id: OUT-2026-09-09-spec-experiment-registry
step: spec
records: [REQ-REPRO-001, REQ-BIAS-011]
commit: null
---

## What was done

`specs/053-experiment-registry/spec.md`: three user stories, 13 functional
requirements, 15 success criteria, tracing both requirements.

## What was decided

- **Absence is stated, never blank** (FR-002). "Fits no model" and "artifact
  unrecorded" are opposite facts a blank field reports identically.
- **A dirty tree makes a result unreportable** (FR-003), which is the
  unreproducible case that looks most convincing.
- **Rule 11 becomes a claim about a field** (FR-012), because storage cannot be
  verified and a claim can.
- **The specification states its own limit.** Nothing here stops someone who
  never mentions a variant, and saying otherwise would be worse than the honour
  system it replaces.

## What is still open

- Nothing from this step.
