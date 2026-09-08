---
traces: [REQ-WP-019, REQ-NRT-F]
status: draft
---

# Feature Specification: Turning-point baselines and the GMDH derivative experiment

**Feature Branch**: `wp-019-derivative-experiment`

**Created**: 2026-09-08

**Input**: REQ-WP-019 items 10-13 — PRD §13A.11, §13A.12, §13A.13 — and
REQ-NRT-F (Test F, PRD §13A.28). These are the two acceptance criteria
[[ADR-023]] left unmet: "direct baseline metrics exist" and "derivative
experiment can return `NO_EDGE` without blocking product completion".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Know whether the direct target has any signal at all (Priority: P1)

Fit the direct turning-point target on point-in-time rows across walk-forward
folds, and report metrics against the baselines it must beat.

**Why this priority**: PRD §13A.13 — "Do not depend only on a derivative-based
target." Without this the derivative experiment has nothing to be compared to,
and REQ-WP-019's fourth acceptance criterion is unmet.

**Acceptance Scenarios**:

1. **Given** labelled point-in-time rows, **When** the direct baseline runs over walk-forward folds, **Then** it reports a score per fold against the no-skill base rate.
2. **Given** a target with no signal, **When** the baseline runs, **Then** it reports that it does not beat the base rate rather than reporting a number alone.
3. **Given** a row missing a feature other rows carry, **When** the design matrix is built, **Then** it is refused — a missing feature must not become a zero.
4. **Given** folds built by `WalkForwardFolds`, **When** the baseline runs, **Then** no fold is fitted and scored on the same row.

---

### User Story 2 - Read a forward path's derivative roots (Priority: P1)

From a cubic forward path, the horizons where the first derivative is zero,
classified by the second derivative.

**Why this priority**: PRD §13A.11 gives the path, the derivatives and the
conditions verbatim. It is the hypothesis the whole experiment tests.

**Acceptance Scenarios**:

1. **Given** path coefficients, **When** roots are requested, **Then** each satisfies `dP/dh = 0` and `0 < h* <= H`.
2. **Given** a root with negative curvature, **When** it is classified, **Then** it is a maximum candidate; positive curvature gives a minimum.
3. **Given** a root whose curvature is zero, **When** it is classified, **Then** it is not a candidate — §13A.11's plateau, which is not a reversal.
4. **Given** a path whose derivative has no root inside the horizon, **When** roots are requested, **Then** none are returned.
5. **Given** a path with two roots inside the horizon, **When** roots are requested, **Then** both are returned — §13A.11 says multiple roots may exist.

---

### User Story 3 - Refuse to promote a root that moves when the inputs barely move (Priority: P1)

Perturb the coefficients within a configured tolerance, recompute the roots for
each member, and record how stable they were.

**Why this priority**: PRD §13A.28 Test F, and §13A.11's own critical
limitation — "a root can appear from tiny coefficient changes". A root promoted
without this is exactly the silent instability the test names.

**Acceptance Scenarios**:

1. **Given** a stable path, **When** stability is assessed, **Then** presence rate, horizon IQR and turn-type agreement are recorded.
2. **Given** a path whose root appears in only some perturbed members, **When** promotion is attempted, **Then** it is refused and the failing conditions are named.
3. **Given** any assessment, **When** it completes, **Then** the metrics are recorded whether or not the root was promoted.
4. **Given** one tolerance and one path, **When** stability is assessed twice, **Then** the metrics are identical.
5. **Given** a root inside the horizon but with curvature below the configured minimum, **When** promotion is attempted, **Then** it is refused with that condition named.

---

### User Story 4 - Let the experiment conclude nothing without blocking the product (Priority: P1)

Run the forward-path derivative experiment end to end and return a verdict that
may be `NO_EDGE`.

**Why this priority**: REQ-WP-019's fifth acceptance criterion, in its own
words: the experiment "can return `NO_EDGE` without blocking product
completion".

**Acceptance Scenarios**:

1. **Given** data with no signal, **When** the experiment runs, **Then** it returns `NO_EDGE` with a reason, and raises nothing.
2. **Given** a model that does not beat the base rate, **When** the experiment runs, **Then** the verdict is `NO_EDGE` whatever the roots did.
3. **Given** roots that none survive the promotion gate, **When** the experiment runs, **Then** the verdict is `NO_EDGE` and the rejected roots are reported with their reasons.
4. **Given** any outcome, **When** it is read, **Then** it carries the comparison report and the stability metrics, so the conclusion can be checked rather than trusted.

---

### Edge Cases

- What happens when the forward path is a straight line? Its derivative is a non-zero constant, so there is no root and no candidate. Correct: a path with no turn should produce no turn.
- What happens when the cubic term is zero? The derivative is linear and has at most one root. Handled as its own case rather than by dividing by zero.
- What happens when every perturbed member finds a root, but at wildly different horizons? Presence rate passes and horizon dispersion fails. Both are recorded, and the gate refuses on the second — which is why §13A.12 lists three metrics and not one.
- What happens when there are too few rows to fit? The experiment returns `NO_EDGE` with that as the reason. "Not enough data" is a finding, not a crash.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The direct baseline MUST fit and score over walk-forward folds, and MUST NOT fit and score on the same row.
- **FR-002**: The direct baseline MUST report a per-fold comparison against the no-skill base rate, and an aggregate over folds.
- **FR-003**: A row missing a feature that the matrix declares MUST be refused, never defaulted.
- **FR-004**: The forward path MUST expose `P_hat(h)`, `dP_hat/dh` and `d²P_hat/dh²` as PRD §13A.11 defines them.
- **FR-005**: Derivative roots MUST satisfy `dP_hat/dh(h*) = 0` and `0 < h* <= H`.
- **FR-006**: A root MUST be classified a maximum when `d²P_hat/dh² < 0` and a minimum when `> 0`; a zero second derivative MUST NOT produce a candidate.
- **FR-007**: Multiple roots inside the horizon MUST all be returned.
- **FR-008**: Stability MUST be assessed by perturbing the coefficients within a configured relative tolerance, over a deterministic set of members.
- **FR-009**: Root sensitivity metrics — presence rate, horizon IQR, turn-type agreement — MUST be recorded on every assessment, promoted or not.
- **FR-010**: Promotion MUST require every configured condition, and a refusal MUST name the conditions that failed.
- **FR-011**: The promotion thresholds MUST be configuration carrying PRD §13A.12's research defaults, not constants.
- **FR-012**: The experiment MUST return a verdict of `EDGE` or `NO_EDGE` and MUST NOT raise when the answer is that there is no edge.
- **FR-013**: A `NO_EDGE` verdict MUST carry a reason, the comparison report and the stability metrics.
- **FR-014**: The experiment MUST report `NO_EDGE` when the model does not beat the no-skill base rate, whatever the roots did.
- **FR-015**: No module may consult a system clock or a random number generator.

### Key Entities

- **Path coefficients**: a cubic forward path over a bounded horizon.
- **Root candidate**: a horizon, a turn type, the curvature there, and the predicted excursion.
- **Root stability**: the three §13A.12 metrics, the tolerance and the member count they were computed over.
- **Experiment outcome**: a verdict, its reason, the comparison report, the stability metrics and every rejected root with its failing conditions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Direct baseline metrics exist for the turning-point target, per fold and in aggregate. *(REQ-WP-019 criterion 4)*
- **SC-002**: A signal-free target reports "does not beat the base rate".
- **SC-003**: A missing feature refuses.
- **SC-004**: Roots match a hand-solved quadratic, inside the horizon and classified by curvature.
- **SC-005**: A zero-curvature root produces no candidate.
- **SC-006**: Stability metrics are recorded on every assessment and are identical across repeated runs.
- **SC-007**: A root that appears in only some members is refused, with the failing condition named.
- **SC-008**: The experiment returns `NO_EDGE` on signal-free data without raising. *(REQ-WP-019 criterion 5)*
- **SC-009**: A model that does not beat the base rate yields `NO_EDGE` even when a root would have been promoted.
- **SC-010**: No module references a clock or a random number generator.

## Assumptions

- **The forward path's coefficients are supplied or fitted from realized paths**, which is label-side and future-aware by PRD §24.2's own permission. Features stay point-in-time; this is the target.
- **§13A.12's conditions 2, 7 and 8** — extrapolation bounds, data-quality state, walk-forward promotion gate — are expressed as inputs to the gate rather than reimplemented here.
- **Ensemble members come from a deterministic perturbation lattice**, not from bootstrap resampling. §13A.12 says "bootstrap/ensemble"; a deterministic lattice satisfies the stability question and keeps Principle XI's reproducibility without an RNG seed to argue about.
