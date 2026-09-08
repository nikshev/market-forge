---
traces: [REQ-WP-018]
status: draft
---

# Feature Specification: GMDH layer

**Feature Branch**: `wp-018-gmdh`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-018 — model abstraction; polynomial node search; complexity
constraints; validation criterion; feature interaction export; comparison
report.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Select nodes on data they were not fitted on (Priority: P1)

Every candidate polynomial is fitted on one split and scored on another. The
score that decides whether it survives never comes from the data that shaped
it.

**Why this priority**: This is what "external criterion" means in GMDH, and it
is the entire reason the method resists overfitting. A search that selected on
training error would grow layers until it memorised the sample, and every
number it produced afterwards would look excellent.

**Independent Test**: Fit on a split, and assert the selection score is
computed from rows the node never saw.

**Acceptance Scenarios**:

1. **Given** a training and a validation split, **When** a node is scored, **Then** the score comes from the validation split.
2. **Given** a node that fits its training split perfectly and its validation split badly, **When** selection runs, **Then** it is pruned.
3. **Given** overlapping splits, **When** a search is started, **Then** it is refused — a split that shares rows is not a split.
4. **Given** REQ-WP-017's purged folds, **When** they are used, **Then** the search runs unchanged: the folds already guarantee what this needs.

---

### User Story 2 - Grow layers under a complexity budget (Priority: P1)

The search builds layers of two-input polynomial nodes, keeps the best, and
stops when the criterion stops improving or the budget is spent.

**Why this priority**: PRD §23.1 puts GMDH's role as interaction discovery and
feature selection, and both need a search that terminates for a stated reason.

**Acceptance Scenarios**:

1. **Given** a maximum layer count, **When** the search runs, **Then** it never exceeds it.
2. **Given** a maximum surviving nodes per layer, **When** a layer is built, **Then** at most that many survive.
3. **Given** a layer whose best score is no better than the previous layer's, **When** the search runs, **Then** it stops and says so.
4. **Given** a completed search, **When** its result is read, **Then** it names why it stopped.
5. **Given** fewer than two inputs, **When** a search is started, **Then** it is refused.

---

### User Story 3 - See which interactions survived (Priority: P2)

The model reports which pairs of inputs its surviving nodes combine.

**Why this priority**: PRD §23.1's first named role is interaction discovery,
and §23.7 lists the candidate interactions the project cares about. A model
that predicts without saying what it used is not doing that job.

**Acceptance Scenarios**:

1. **Given** a trained model, **When** interactions are exported, **Then** each names the two inputs it combines and the layer it came from.
2. **Given** a model whose first layer feeds its second, **When** interactions are exported, **Then** they resolve to original input names, not to node indices.

---

### User Story 4 - Compare against baselines before believing anything (Priority: P1)

Every GMDH result is reported beside the baselines PRD §23.6 requires, on the
same split.

**Why this priority**: §23.6 says "Every GMDH result must beat" a list starting
with the no-skill base rate. Constitution Principle IV says no model layer
until deterministic baselines exist and leakage tests pass. A GMDH number
without its baselines is not a result.

**Acceptance Scenarios**:

1. **Given** a trained model, **When** the comparison report is produced, **Then** it carries the model's score and each baseline's, on identical data.
2. **Given** a model no better than the base rate, **When** the report is read, **Then** it says so explicitly.
3. **Given** a report, **When** it is read, **Then** it names which baselines were run and which were not.

---

### Edge Cases

- What happens when two inputs are identical? The node reduces to a single-input polynomial; it is allowed and its interaction export records both names, so a reader can see the degeneracy rather than discovering it in the coefficients.
- What happens when a node's fit is singular? The node is dropped, counted, and the search continues — a singular fit means those two inputs carry no independent information on that split.
- What happens when every node in a layer is dropped? The search stops at the previous layer and reports the reason.
- What happens when the validation split has one row? The search is refused: a criterion computed on one row selects noise.
- What happens when the target is constant? The search is refused, because every model predicts it perfectly and the comparison would be meaningless.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A node's selection score MUST be computed on rows not used to fit it.
- **FR-002**: Splits that share rows MUST be refused.
- **FR-003**: A search MUST respect a maximum layer count and a maximum surviving nodes per layer.
- **FR-004**: A search MUST stop when a layer fails to improve on the previous layer's best score.
- **FR-005**: A completed search MUST report why it stopped.
- **FR-006**: A search with fewer than two inputs, a single-row validation split, or a constant target MUST be refused.
- **FR-007**: A singular node fit MUST be dropped and counted, not approximated.
- **FR-008**: Interactions MUST be exportable, resolving through layers to original input names.
- **FR-009**: A comparison report MUST carry the model's score and each baseline's, computed on identical data.
- **FR-010**: The report MUST state explicitly when the model does not beat the base rate.
- **FR-011**: The report MUST name which of PRD §23.6's baselines were run and which were not.
- **FR-012**: Training MUST be deterministic: the same data and configuration give the same model.
- **FR-013**: No module may consult a system clock.

### Key Entities

- **Node**: two inputs, a fitted polynomial, and its score on data it did not see.
- **Layer**: the nodes that survived selection.
- **Search result**: the layers, why the search stopped, and what it dropped.
- **Comparison report**: one score per model on one split.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A node scoring perfectly on training and poorly on validation is pruned.
- **SC-002**: Overlapping splits are refused.
- **SC-003**: A search never exceeds its layer or width budget.
- **SC-004**: A search that stops early names its reason.
- **SC-005**: Exported interactions resolve to original input names.
- **SC-006**: The comparison report carries the model and every run baseline on identical data.
- **SC-007**: A model no better than the base rate is reported as such.
- **SC-008**: Two trainings on one dataset give identical models.
- **SC-009**: No module references a system clock.

## Assumptions

- **Baselines are the no-skill base rate and logistic regression.** PRD §23.6
  also lists a decision tree, gradient boosted trees, and optionally
  LightGBM/XGBoost "if dependency allowed". Implementing tree ensembles here
  would be a second project; adding a dependency for them is a decision this
  spec does not make. The report names them as not run.
- **The target is binary classification.** PRD §23.2's rejection success and
  §23.5A's turning-point probability are both binary; §23.4's regressions are
  not built.
- **This is not wired into signals.** PRD §13A.11's derivative hypothesis,
  §13A.12's root filtering and the walk-forward promotion gate are separate
  work; a model here trains, scores and reports, and nothing consumes it.
- **Principle IV is satisfied, and that is why this exists now.** Deterministic
  baselines exist (REQ-WP-006, REQ-WP-007, REQ-WP-019) and their leakage tests
  pass (REQ-NRT-A to E, REQ-WP-017's checks).
