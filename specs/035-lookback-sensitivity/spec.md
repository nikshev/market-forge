---
traces: [REQ-EXP-002]
status: draft
---

# Feature Specification: Lookback sensitivity

**Feature Branch**: `exp-002-lookback-sensitivity`

**Created**: 2026-09-09

**Input**: REQ-EXP-002 — six lookbacks, and the instruction "do not select solely
on maximum PnL; evaluate stability plateau".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure every lookback the same way (Priority: P1)

40, 60, 80, 100, 150 and 200 bars, over one series, reporting the same metrics.

**Why this priority**: the experiment is the sweep. A lookback missing from the
report is one the recommendation never considered.

**Acceptance Scenarios**:

1. **Given** the six lookbacks, **When** the sweep runs, **Then** each has an entry.
2. **Given** one series, **When** the sweep runs, **Then** every lookback is measured on the same bars and the same split.
3. **Given** a lookback the series is too short for, **When** the sweep runs, **Then** it is reported as unmeasurable and the others still run.
4. **Given** one input, **When** the sweep runs twice, **Then** the reports are equal.

---

### User Story 2 - Find the plateau, not the peak (Priority: P1)

The widest run of adjacent lookbacks whose result stays within a tolerance.

**Why this priority**: EXP-002's own instruction. A peak is where the noise
happened to help; a plateau is where the choice does not matter much, which is
the only kind of choice that survives contact with new data.

**Acceptance Scenarios**:

1. **Given** results across the lookbacks, **When** the plateau is found, **Then** it is the widest run of adjacent lookbacks within the tolerance of each other.
2. **Given** a jagged sweep with no run of adjacent lookbacks inside the tolerance, **When** the plateau is requested, **Then** none is reported.
3. **Given** two plateaus of equal width, **When** one is chosen, **Then** the choice is by a declared rule rather than by position.
4. **Given** a tolerance, **When** it is widened, **Then** the plateau can only grow.

---

### User Story 3 - Refuse to recommend a peak (Priority: P1)

The recommendation comes from the plateau, and the report says where the peak
was so a reader can see they differ.

**Why this priority**: "do not select solely on maximum PnL" is a rule about the
selection, and a report that names the best PnL and nothing else *is* selection
by PnL, whatever the surrounding text says.

**Acceptance Scenarios**:

1. **Given** a sweep whose best expectancy is off the plateau, **When** a lookback is recommended, **Then** the plateau's is recommended and the peak is named separately.
2. **Given** no plateau, **When** a lookback is recommended, **Then** none is recommended, with the reason — not the peak as a fallback.
3. **Given** any recommendation, **When** it is read, **Then** it carries the plateau it came from.
4. **Given** a sweep without costs, **When** it is run, **Then** it is refused, because expectancy is an economic metric.

---

### Edge Cases

- What happens when every lookback ties exactly? The whole sweep is one plateau, its centre is recommended, and the report says the tolerance covered everything — which is a finding about the tolerance, not about the market.
- What happens when only one lookback could be measured? No plateau: a run of one is not a plateau, and recommending it would be selecting the only candidate that happened to fit.
- What happens when the peak is inside the plateau? Both are reported and they agree. The rule does not forbid the peak from winning; it forbids the peak from being the reason.
- What happens when a lookback produces no trades? Its expectancy is absent, and an absent value cannot join a plateau — a plateau across a gap is two plateaus.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All six of EXP-002's lookbacks MUST be swept, and the set MUST be configurable.
- **FR-002**: Every lookback MUST be measured on the same bars, split and settings.
- **FR-003**: A lookback that cannot be measured MUST be reported with the reason and MUST NOT stop the sweep.
- **FR-004**: The plateau MUST be the widest run of adjacent measured lookbacks whose values lie within a configured tolerance of each other.
- **FR-005**: A plateau MUST span at least two adjacent lookbacks.
- **FR-006**: A tie between equally wide plateaus MUST be broken by a declared rule.
- **FR-007**: The recommendation MUST come from the plateau, never from the peak.
- **FR-008**: The report MUST name the peak separately, so the two can be compared.
- **FR-009**: With no plateau, no lookback MUST be recommended, and the peak MUST NOT be substituted.
- **FR-010**: An absent value MUST break a plateau rather than be skipped over.
- **FR-011**: The sweep MUST be refused without a cost model.
- **FR-012**: The report MUST be deterministic.

### Key Entities

- **Sweep entry**: one lookback's metrics, or why it has none.
- **Plateau**: the lookbacks in it, its width, and the tolerance that defined it.
- **Recommendation**: a lookback, the plateau behind it, and the peak beside it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Six entries, one per lookback.
- **SC-002**: An unmeasurable lookback is reported and the rest still run.
- **SC-003**: The plateau is the widest qualifying run, verified on a hand-built sweep.
- **SC-004**: A jagged sweep yields no plateau.
- **SC-005**: A wider tolerance never shrinks the plateau.
- **SC-006**: When the peak is off the plateau, the recommendation is the plateau's and the peak is named.
- **SC-007**: With no plateau there is no recommendation, and the peak is not substituted.
- **SC-008**: An absent value splits a plateau in two.
- **SC-009**: A sweep without costs refuses.
- **SC-010**: Two runs produce equal reports.

## Assumptions

- **The metric the plateau is measured over is expectancy after costs**, which is what "maximum PnL" refers to; the rule is about how it is used, not about replacing it.
- **The channel model is held fixed across the sweep.** EXP-002 varies the lookback; [[REQ-EXP-001]] varies the model.
- **Adjacency is by position in the configured list**, not by numeric distance. 150 and 200 are adjacent in EXP-002's list though fifty bars apart, and that is the sweep's own resolution.
