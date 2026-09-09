---
id: OUT-2026-09-09-spec-training-gate
step: spec
records: [REQ-US-007]
commit: null
---

## What was done

`specs/031-training-gate/spec.md`: two user stories, 9 functional requirements,
8 success criteria.

## What was decided

- **The precondition becomes a type.** Everything else — a documented step, a
  test that asserts the checks were called — is a convention, and REQ-US-007
  asks for a guarantee.
- **No hand-assembled certificate.** A gate with a back door is documentation.
- **The certificate carries its folds**, so what was certified is what is
  trained on.
- **"Training" is fitting.** A procedure that reads a dataset without fitting
  needs no certificate; the gate sits where a leak becomes a number someone
  believes.

## What is still open

- **The GMDH search takes arrays, not folds**, so the gate sits at the fold
  level. A caller who builds arrays by hand and calls `fit_with_selection`
  directly bypasses it — which is why the entry points that assemble those
  arrays are the ones gated.
