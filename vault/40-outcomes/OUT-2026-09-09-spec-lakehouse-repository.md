---
id: OUT-2026-09-09-spec-lakehouse-repository
step: spec
records: [REQ-STORE-002]
commit: null
---

## What was done

`specs/055-lakehouse-repository/spec.md`: three user stories, 12 functional
requirements, 10 success criteria.

## What was decided

- **Two requirements exist to make the others checkable** (FR-002, FR-003): one
  suite over both implementations, and every endpoint test parametrised.
- **A score's contributions join on the score's own id** (FR-008), which came
  out of a defect rather than foresight.
- **A decimal column refuses anything but its exact text on read** (FR-012),
  because `Decimal(str(1.1))` succeeds and would undo the column type silently
  on the way out.

## What is still open

- Nothing from this step.
