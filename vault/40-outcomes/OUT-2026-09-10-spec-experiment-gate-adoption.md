---
id: OUT-2026-09-10-spec-experiment-gate-adoption
step: spec
records: [REQ-BIAS-011]
commit: null
---

## What was done

`specs/057-experiment-gate-adoption/spec.md`: three user stories, 14 functional
requirements, 9 success criteria, for the half [[ADR-054]] named and left
undone — the eighteen research entry points reporting their field through
[[REQ-REPRO-001]]'s gate.

[[REQ-BIAS-011]] was already `specified`, on the strength of
[[SPEC-053-experiment-registry]], which specifies the *mechanism* and says
nothing about adoption. This spec is what the requirement needs to go further,
so the rung does not move on this step.

## What was decided

- **Adoption is the field becoming askable, not eighteen calls to `record`.**
  ADR-054's own words are the test: a registry that is merely available is an
  honour system with a database attached. If a comparison cannot be *asked* for
  its field, a module that skips the registry looks exactly like one that has
  nothing to report.
- **A comparison that names no winner is not made to name one** (FR-004,
  FR-009). Several deliberately report a field and no choice —
  `extremum_detectors` says so in its docstring. Forcing a winner would
  manufacture the very claim rule 11 exists to make checkable. Recording is
  universal; the gate applies to a result that chose.
- **A variant's config is what distinguishes it, not its name** (FR-003,
  SC-003). Where a comparison keeps a variant's name and discards its
  parameters, it starts keeping them. The cheaper reading — hash the name —
  puts N indistinguishable rows in the registry and looks like full coverage,
  which is a worse outcome than no coverage because it reads as checked.
- **The suite discovers the modules rather than listing them** (FR-012, SC-008).
  Eighteen adopting today is a snapshot; the next module decides whether the
  rule is enforced or was enforced once. A hand-maintained list is a thing
  someone forgets, and forgetting is silent.
- **All eighteen or none.** A subset would claim the coverage [[ADR-024]]
  refused for rule 2 on the strength of one engine's guard, and ADR-054 already
  refused for this rule.

## What is still open

- **Where a variant's parameters are recoverable is not yet surveyed.**
  `ChannelComparisonReport` keeps `settings` shared across the field and a name
  per entry; the model objects carrying the parameters are not kept. How many of
  the eighteen are in that position is plan work, and it is the main thing that
  could make this larger than it looks.
- **The seam's inputs come from a caller that does not exist yet.** Dataset,
  code version and model artifact are the caller's to supply; nothing in the
  repository assembles them for a research run today. This spec assumes a
  caller; it does not build one.
- **Nothing yet forces a *reported* result through the seam.** FR-012's check
  reaches every module's comparison; it cannot reach a human who reads a report
  object and quotes one variant in a document. That gap is rule 11's honest
  limit, already stated in ADR-054, and this spec does not close it.
