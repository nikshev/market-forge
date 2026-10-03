---
traces: [REQ-INFRA-011]
status: draft
---

# Feature Specification: A scaling guard measures its sizes under the same conditions

**Feature Branch**: `129-perf-guard-rounds`

**Created**: 2026-10-03

**Status**: Draft

**Input**: [[REQ-INFRA-011]], on [[REQ-WP-057]].

## Context

A scaling guard asks whether doubling the work costs about double. Its answer is a ratio of two timings,
and the argument for trusting it on a busy machine is that both timings come from the same run, so the
machine's state cancels. That holds only if both were measured under the same state. Measured one size
after another, they were not: whatever the host was doing while the second size ran belongs to the
second size alone.

The fault is not subtle once the measurement order is written down. It is also not rare on this host,
where the load average sits around four: six gates or full runs failed in one session, on two timing
tests that passed every time they were run alone.

### What the fix is, and is not

It is a change to *how the sizes are interleaved and which quantile is compared*, and nothing else. The
targets, the thresholds and the assertion that a doubling may cost at most three times are unchanged. It
is not skipping the tests, widening the bound, or retrying: each of those makes the guard weaker, and the
point of the guard is that a quadratic operation fails it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A burst of load no longer fails a linear operation (Priority: P1)

**Independent Test**: a fake clock; a perfectly linear operation at three sizes; a burst of extra cost over
twenty consecutive calls.

**Acceptance Scenarios**:

1. **Given** the burst covers exactly the second size's runs, **When** the sizes are measured one after
   another, **Then** the ratio is far from two — the fault, reproduced deterministically.
2. **Given** the same burst, **When** the sizes are measured in rounds, **Then** every ratio stays near two.
3. **Given** the burst starts anywhere in the run, **Then** the rounds still agree.

---

### User Story 2 - The guard still bites (Priority: P1)

**Acceptance Scenarios**:

1. **Given** an operation whose cost grows as the square of the size, **When** measured in rounds with no
   noise, **Then** the ratios are near four.
2. **Given** the same operation with a burst, **Then** they are still at least three.
3. **Given** the real scaling tests, **Then** a deliberately quadratic operation still fails the guard.

---

### User Story 3 - The gate stops failing for no reason (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the three scaling tests run repeatedly under CPU contention, **Then** they fail less often
   than before, counted and recorded.

### Edge Cases

- A single size: no ratio exists; refused as it is today.
- A burst longer than the whole run: every size is equally slow, and the ratio is two.
- A very short run: `repeats` is at least one.
- The lower quantile of a run with a few samples: nearest-rank, as the existing percentile is.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: There MUST be a way to measure several operations in rounds, one run of each per round, with
  the starting operation rotating, returning measurements in the order given.
- **FR-002**: `scaling_ratio` MUST accept the quantile it compares, defaulting to the median so existing
  callers are unchanged.
- **FR-003**: A fake-clock test MUST show sequential measurement fooled by a burst and measurement in
  rounds not fooled, for a burst falling anywhere.
- **FR-004**: A quadratic operation MUST still be reported as at least three times per doubling, with and
  without a burst.
- **FR-005**: The three scaling tests MUST measure in rounds and compare the lower quartile.
- **FR-006**: Nothing about the targets or the bound of three may change.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Against a burst covering one size, the sequential ratio exceeds 3 and the rounds' ratios are
  all below 3 (deterministic).
- **SC-002**: A quadratic operation gives ratios of at least 3 in every case tested.
- **SC-003**: Over repeated runs of the three scaling tests under CPU contention, failures are fewer than
  with the old measurement, recorded as a count.

## Assumptions

- The host's contention is bursty on the scale of seconds, which is what the failures' shape implies.
- The other performance tests assert targets with fiftyfold headroom and are not affected.
