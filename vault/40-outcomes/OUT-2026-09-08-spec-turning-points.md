---
id: OUT-2026-09-08-spec-turning-points
step: spec
records: [REQ-WP-019, REQ-NRT-A, REQ-NRT-B, REQ-NRT-C, REQ-NRT-D, REQ-NRT-E]
commit: null
---

## What was done

`specs/014-turning-points/spec.md`: four user stories, 14 functional
requirements, 10 success criteria, two ADRs.

## What was decided

- **REQ-WP-019 will not reach `implemented`** ([[ADR-023]]). Two of its five
  PRD acceptance criteria — direct baseline metrics, and a GMDH derivative
  experiment able to return `NO_EDGE` — need REQ-WP-017 and REQ-WP-018.
  Principle IV forbids both until the deterministic baseline passes leakage
  tests, and that baseline is this feature. Marking the work package complete
  on a third of its scope would make the traceability graph say something
  false.
- **The five NRT constraints advance on their own.** Each is a single testable
  property with its own test, which is what `hard_gated` asks for. They have
  sat at `draft` since extraction because nothing produced them a test.
- **Test D is a declaration, not an inspection** ([[ADR-022]]). PRD §13A.28
  says the production path fails when a transform *declares* symmetric or
  centered future dependence. Inferring centredness in general is not
  achievable — a centered moving average, a symmetric Savitzky-Golay window,
  `argrelextrema` and a loop reading `series[i + 1]` are the same defect and
  look nothing alike — and a checker catching three would give false
  confidence about the fourth. Test A is the backstop for a false declaration.
- **Research paths stay unguarded, deliberately.** §13A.4's symmetric labels
  are centered by definition and legal; §13A.6 permits centered peak-finding
  for labels and diagnostics and forbids it reaching live signals. Only the
  production path guards.

## What is still open

- **REQ-NRT-F** tests GMDH derivative root stability and stays at `draft` with
  REQ-WP-018.
- **§13A.30's steps 3 to 5** — causal local-polynomial slope, Kalman, and
  channel-conditioned extremum classes — are in REQ-WP-019's ordering and are
  not built. Step 2 is what the non-repainting tests can be written against.
- **`TurningPointForecast` is not implemented**: it is a model output and there
  is no model.
