---
traces: [REQ-BIAS-002]
status: draft
---

# Feature Specification: No centred filter reaches a live feature

**Feature Branch**: `bias-002-live-causality`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-BIAS-002 — "No centered moving filters in live features" (PRD §41 rule 2).

## Context

[[ADR-024]] gave six of PRD §41's eleven anti-bias rules a home. Rule 2 was one
of them, and the coverage it claimed was narrow on purpose:

> ADR-024 refused to claim coverage for rule 2 on the strength of one engine's
> guard.

That refusal is still correct, and this specification says exactly what is
missing. Three things exist today and are not in question:

- `require_causal` refuses a transform declaring `centered=True`;
- `Transform.centered` has no default, so an author cannot skip the question;
- `FeatureSpec.point_in_time_safe` is a required field on every registration.

What is missing is that **none of the three reaches the live feature path**:

- `require_causal` has exactly one call site in the repository, and it is inside
  a research comparison (`derivative_turning`), not on the production path.
- The forbidden-import scan reads `src/channelflow/extrema/` and nothing else.
  `features/`, `channels/`, `signals/`, `volume/` and `derivatives/` all compute
  live values and none is scanned; `savgol_filter` in `features/flow.py` would
  pass every check in the repository.
- Every registered feature declares `point_in_time_safe=True` and **no rule
  reads the field**. A registration saying `False` would be accepted in silence.

The rule names live features. Nothing checks the live features.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A centred helper cannot enter a live package unnoticed (Priority: P1)

Someone reaches for `savgol_filter` because a causal filter is not smoothing
enough. The suite fails, names the file, and says which rule it broke.

**Why this priority**: This is the realistic mistake. It is not dishonest and it
is not exotic — it is what a good engineer does when a filter looks too noisy,
and the current suite would let it through everywhere except one package.

**Independent Test**: Add a forbidden import to any live package; the suite goes
red naming that file.

**Acceptance Scenarios**:

1. **Given** a live package, **When** it imports a centred-smoothing or offline peak-finding helper, **Then** the suite fails naming the file and the helper.
2. **Given** a research package, **When** it does the same, **Then** the suite passes — centred filters may create labels and diagnostics (PRD §13A.6).
3. **Given** a package added after this work, **When** nobody lists it anywhere, **Then** it is scanned by default.

---

### User Story 2 - A feature cannot be registered as unsafe and used live (Priority: P1)

The registry already asks every feature whether it is point-in-time safe. The
answer now has to be `True`, and a feature that cannot say so has to say where
it belongs instead.

**Why this priority**: A required field nothing reads is documentation, and
[[ADR-015]] made the registry a gate rather than a habit for exactly this
reason.

**Independent Test**: Register a feature with `point_in_time_safe=False`; the
suite fails naming it.

**Acceptance Scenarios**:

1. **Given** the registry, **When** any registered feature declares `point_in_time_safe=False`, **Then** the suite fails naming the feature.
2. **Given** the registry, **When** every feature declares `True`, **Then** the suite passes and says how many it checked.

---

### User Story 3 - The exemption is explicit and small (Priority: P2)

A package that legitimately uses centred filters is exempt because someone wrote
down that it is, and why.

**Why this priority**: The exemption is where this rule will be eroded. A silent
one is indistinguishable from an oversight.

**Acceptance Scenarios**:

1. **Given** the exemption list, **When** it names a package, **Then** the reason is recorded beside it.
2. **Given** the exemption list, **When** it names a package that no longer exists, **Then** the suite fails rather than carrying a stale entry.

### Edge Cases

- **A helper named in a string or a comment.** `causality.py` names all of them in order to forbid them, and a docstring explaining the rule must not trip it.
- **A live package importing a research module.** The rule is about what computes a live value, and an import edge is not a call. This is named as out of scope rather than silently allowed.
- **A package with no modules.** Scanning it must not pass vacuously.
- **A feature registered outside `features/`.** `derivatives/`, `volume/` and others register features too; the check reads the registry, not a directory.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every package under `src/channelflow/` MUST be scanned for centred-smoothing and offline peak-finding helpers.
- **FR-002**: A module MUST be exempt only by being named in an explicit list, with a recorded reason. The exemption is per module, not per package: exempting a package would exempt the modules beside the one that needs it.
- **FR-003**: An exemption naming a module that does not exist MUST fail the suite.
- **FR-004**: The scan MUST name the file and the helper when it fails.
- **FR-005**: The scan MUST fail rather than pass when it finds no modules to scan.
- **FR-006**: Every registered feature MUST declare `point_in_time_safe=True`.
- **FR-007**: The registry check MUST read the registry rather than a directory listing.
- **FR-008**: `causality.py` MUST remain able to name the forbidden helpers in order to forbid them.
- **FR-009**: Nothing in this feature MUST change what any feature computes.

### Key Entities

- **Live module**: a module under `src/channelflow/` that is not on the exemption list.
- **Exemption**: a module path and the reason centred helpers are legitimate in it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The number of packages scanned equals the number of packages under `src/channelflow/` less the exemptions.
- **SC-002**: A forbidden helper added to any live package turns the suite red, and the failure names the file.
- **SC-003**: The same helper in an exempt module leaves the suite green, and in another module of the same package does not.
- **SC-004**: An exemption for a module that does not exist turns the suite red.
- **SC-005**: Every feature in the registry declares `point_in_time_safe=True`, and the check reports the count.
- **SC-006**: A feature registered with `point_in_time_safe=False` turns the suite red, naming the feature.
- **SC-007**: Every existing feature's value is unchanged.

## Assumptions

- **The declaration is a claim, and a false one is not caught here.** `causality.py` says so already: a transform peeking forward while declaring itself causal is Test A's business, not this one's. This feature widens the reach of two existing guards; it does not make them detectors.
- **The forbidden list stays a short list of specific helpers**, not a general detector. [[ADR-022]] settled that: a centred moving average, a symmetric Savitzky-Golay window, `argrelextrema`, and a loop reading `series[i + 1]` are the same defect and look nothing alike.
- **An import edge is not a call.** A live package importing a research module is out of scope here, and named as such rather than left ambiguous.
- **The exemption list will be short and is expected to shrink.** Research modules are the legitimate case for centred filters under PRD §13A.6; anything else on it is a finding.
