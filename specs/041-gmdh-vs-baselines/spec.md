---
traces: [REQ-EXP-008]
status: draft
---

# Feature Specification: GMDH against the baselines

**Feature Branch**: `exp-008-gmdh-vs-baselines`

**Created**: 2026-09-09

**Input**: REQ-EXP-008 — four models on one matrix, and four metrics beside the
Brier score.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare against baselines that can actually compete (Priority: P1)

Logistic, elastic net, gradient boosting and GMDH, on one feature matrix.

**Why this priority**: a GMDH result is only as meaningful as the baselines it
beat. [[ADR-029]] said it plainly — a model that beats a poor tree looks
validated.

**Acceptance Scenarios**:

1. **Given** the comparison report, **When** it is read, **Then** the regularized logistic and the boosted trees have run.
2. **Given** an interaction target, **When** the booster is compared with a linear model, **Then** it wins by a wide margin.
3. **Given** the elastic net, **When** its signature is inspected, **Then** its penalty and L1 ratio have no defaults.
4. **Given** either new baseline, **When** it is fitted twice, **Then** the predictions are identical.

---

### User Story 2 - Report what the Brier score cannot say (Priority: P1)

Calibration, PR-AUC, expectancy by probability bucket, feature stability.

**Why this priority**: each answers a different way a model can look good and be
useless — miscalibrated, unable to find a rare positive, confident without
profit, or fitted to the fold.

**Acceptance Scenarios**:

1. **Given** a perfectly calibrated model, **When** calibration is measured, **Then** the error is zero; an overconfident one shows a positive gap.
2. **Given** a band the model never predicted, **When** calibration is measured, **Then** the band is omitted rather than scored as perfect.
3. **Given** an imbalanced target and a model that ranks badly, **When** PR-AUC is measured, **Then** it is low.
4. **Given** no positives at all, **When** PR-AUC is measured, **Then** it is absent, not zero.
5. **Given** buckets of predicted probability, **When** expectancy is measured, **Then** each band carries its own economics or the reason it has none.
6. **Given** folds selecting different features, **When** stability is measured, **Then** it falls; a feature shared with only some folds does not count.

---

### Edge Cases

- What happens when a bucket holds only ambiguous outcomes? It reports its count and no economics.
- What happens with one fold? Stability is absent — across one fold it is not a measurement.
- What happens when a split cannot improve on not splitting? It is not taken, and a tree that cannot improve is not added to the ensemble.
- What happens when the minimum leaf size exceeds the sample? No split is legal and the ensemble predicts one number, which is the guard doing its job.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The comparison MUST run the regularized logistic and the gradient boosted trees.
- **FR-002**: The elastic net's penalty and L1 ratio MUST be required arguments.
- **FR-003**: A negative penalty or an L1 ratio outside `[0, 1]` MUST be refused.
- **FR-004**: The boosted trees MUST be able to represent an interaction between two features.
- **FR-005**: A split that does not improve on not splitting MUST NOT be taken.
- **FR-006**: A minimum leaf size MUST be enforced.
- **FR-007**: Both new baselines MUST be deterministic without a seed.
- **FR-008**: Calibration MUST report per-band gaps and one summary error, omitting empty bands.
- **FR-009**: Calibration over no predictions MUST be refused.
- **FR-010**: PR-AUC MUST be reported, and MUST be absent when nothing is positive.
- **FR-011**: Expectancy MUST be reported per probability bucket, with a reason where a bucket has no resolved outcome.
- **FR-012**: Feature stability MUST count only features present in every fold, and MUST be absent for fewer than two folds.
- **FR-013**: The two baselines still not run MUST carry their reasons.

### Key Entities

- **Calibration**: per-band predicted-versus-observed, and the weighted error.
- **Bucket expectancy**: one probability band's economics.
- **Stability**: the share of each fold's selection that survives every fold.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Four of §23.6's six baselines run; two carry reasons.
- **SC-002**: The booster halves the linear model's Brier on an interaction target.
- **SC-003**: The elastic net's strengths have no defaults, verified over the signature.
- **SC-004**: A stronger L1 penalty zeroes more coefficients.
- **SC-005**: Both baselines fit identically twice.
- **SC-006**: Calibration is zero for a calibrated model and positive for an overconfident one.
- **SC-007**: Empty calibration bands are omitted; no predictions refuses.
- **SC-008**: PR-AUC is one for a perfect ranking, low for a bad one, absent with no positives.
- **SC-009**: A high-confidence bucket out-earns a low-confidence one; an all-ambiguous bucket reports its reason.
- **SC-010**: Stability is one when folds agree, zero when nothing is shared by all, absent for one fold.
- **SC-011**: A leaf size above the sample leaves the ensemble flat.

## Assumptions

- **These are baselines, not models to deploy.** [[ADR-050]] says so: the implementations are textbook, and the LightGBM dependency question stays open.
- **The comparison report declares its own regularization strengths**, because a report has to run with some pair; the model refuses to.
