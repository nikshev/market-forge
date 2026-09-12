---
traces: [REQ-WP-050]
status: draft
---

# Feature Specification: Funding dispersion over a common interval

**Feature Branch**: `wp-050-funding-dispersion`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-050 — Phase 5's last analytical deliverable.

## Context

PRD §16.1 lists "cross-venue funding dispersion" in one line. Four venues now
publish funding and nothing disperses it.

The feature is one line; the reason it needs care is that **the rates are not
comparable as they arrive.** Measured from each venue's own funding history:

    Hyperliquid    60 minutes
    Binance       480 minutes
    Bybit         480 minutes
    OKX           480 minutes

A Hyperliquid rate is hourly and the other three are eight-hourly. Side by side
without normalising, the four differ by a factor of eight before the market has
said anything — and the resulting figure is positive, ordered, believable, and
moves when funding moves. It looks like a signal and behaves like one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The interval is observed (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a venue's settlement history, **When** its interval is derived, **Then** it comes from that history.
2. **Given** four venues, **When** their intervals are compared, **Then** one differs from the rest by a factor of eight.
3. **Given** an irregular schedule, **When** an interval is asked for, **Then** it is refused.
4. **Given** a history whose first gap is an outlier within tolerance, **When** the interval is derived, **Then** the outlier does not become the interval.

---

### User Story 2 - The comparison is over one period (Priority: P1)

**Acceptance Scenarios**:

1. **Given** rates from venues with different intervals, **When** dispersed, **Then** every rate is first put on the caller's interval.
2. **Given** the same rates, **When** dispersed raw and normalised, **Then** the answers differ.
3. **Given** no reporting interval, **When** dispersed, **Then** it is refused.

---

### User Story 3 - Who contributed, and who did not (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a reading older than its venue's own interval, **When** dispersed, **Then** it is excluded with a reason.
2. **Given** a reading from after the instant asked about, **When** dispersed, **Then** it is excluded.
3. **Given** fewer than two contributors, **When** dispersed, **Then** it is refused.

### Edge Cases

- **Venues split on the sign of funding.** Wide, not tight: the spread is signed-aware.
- **A venue publishing no funding.** Excluded, not counted as zero.
- **An interval of zero on a reading.** Refused at construction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Rates MUST be normalised to a caller-supplied interval before comparison.
- **FR-002**: The reporting interval MUST have no default.
- **FR-003**: A venue's interval MUST be observed from its settlements, never assumed.
- **FR-004**: An interval MUST come from the middle of the gaps, not the first.
- **FR-005**: An irregular schedule MUST be refused.
- **FR-006**: Normalisation MUST be linear, not compounded.
- **FR-007**: Staleness MUST be judged against the venue's own interval.
- **FR-008**: A stale or future reading MUST be excluded with a reason, never carried forward.
- **FR-009**: Fewer than two contributors MUST be refused.
- **FR-010**: The result MUST report median, spread and standard deviation, all signed-aware.
- **FR-011**: Fixtures MUST carry settlement history, not a stated interval.

### Key Entities

- **Venue funding**: a rate, the period it covers, and when it was observed.
- **Funding dispersion**: three figures, the per-venue normalised rates, and who was excluded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The four venues' intervals are derived, and two distinct values appear.
- **SC-002**: The raw and normalised spreads differ on real data.
- **SC-003**: A first-gap outlier within tolerance is shown not to become the interval.
- **SC-004**: A stale venue is excluded with its reason recorded.
- **SC-005**: No test opens a socket.

## Assumptions

- **Normalisation is linear.** Funding accrues per period and is paid, not
  reinvested; compounding would model a position that rolls its funding back in,
  which is a different instrument.
- **Staleness is one interval.** A reading older than that means the venue has
  settled again since, so the rate in hand is not the rate in force. Nothing
  arbitrary to tune, and it scales with the venue.
- **Three figures rather than one.** The PRD does not define "dispersion", and a
  single number would hide which of the middle, the extremes or the clustering
  was meant.

## Open Questions

- **Whether the interval belongs on `DerivativesState`.** Today it is derived
  separately from history; carrying it with the rate would make the pairing
  structural rather than a caller's responsibility.
