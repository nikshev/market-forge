---
traces: [REQ-WP-016]
status: draft
---

# Feature Specification: Cross-venue engine

**Feature Branch**: `wp-016-cross-venue`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-WP-016 — PRD §17. Acceptance criteria derived and approved in
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agree on a price across venues (Priority: P1)

A consensus mid is the median of the contributing venues' normalized mids, and
the result names which venues contributed.

**Why this priority**: PRD §17.1, and every basis figure below is measured
against it. A consensus computed from the wrong set is wrong in a way no
downstream number reveals.

**Independent Test**: Venues with known mids, and a consensus compared against
the median computed by hand.

**Acceptance Scenarios**:

1. **Given** three venues with known mids, **When** the consensus is computed, **Then** it is their median and the result names all three.
2. **Given** a venue whose mid is older than the staleness tolerance, **When** the consensus is computed, **Then** it does not contribute, and the contributor count says so.
3. **Given** a venue with no mid at the instant, **When** the consensus is computed, **Then** it does not contribute.
4. **Given** fewer than two contributing venues, **When** a consensus is requested, **Then** it is refused.
5. **Given** venues quoting different representations of one asset, **When** the consensus is computed, **Then** they are recognised as comparable through the registry, not through their tickers.

---

### User Story 2 - Measure each venue against the consensus (Priority: P1)

Basis in basis points for each contributing venue — and, where an AMM is
involved, an executable basis at a supplied notional instead.

**Why this priority**: PRD §17.3 gives the formula; §18.14 forbids applying it
to an AMM. Both are requirements, and the second is the one that is easy to
violate while producing a number that looks right.

**Acceptance Scenarios**:

1. **Given** a contributing venue, **When** its basis is computed, **Then** it is `10000 * (mid_i / consensus_mid - 1)`.
2. **Given** a venue at the consensus, **When** its basis is computed, **Then** it is zero.
3. **Given** an AMM venue, **When** mid-based basis is requested, **Then** it is refused.
4. **Given** an AMM and an order book, **When** executable basis at a notional is requested, **Then** it is computed from each side's executable price.
5. **Given** no notional, **When** executable basis is requested, **Then** it is refused — there is no default size.

---

### User Story 3 - Study which venue moves first, without acting on it (Priority: P2)

Per-venue returns over short windows, and pairwise lagged correlations, marked
research-only.

**Why this priority**: PRD §17.2 lists the features and then forbids the
obvious next step: "Do not convert correlation to trading rule without OOS
validation."

**Acceptance Scenarios**:

1. **Given** a venue's price history, **When** returns over 1, 5 and 10 seconds are computed, **Then** each uses only prices at or before the instant.
2. **Given** two venues' returns, **When** a lagged correlation is computed, **Then** it is over aligned event-time windows.
3. **Given** a lead-lag output, **When** it is read, **Then** it declares itself research-only.
4. **Given** the signal, alerting and stop packages, **When** their sources are inspected, **Then** none imports the lead-lag module.

---

### User Story 4 - See where the liquidity actually is (Priority: P2)

Depth per venue at 10/25/50 bps, the best venue to execute a given size, and
how concentrated liquidity is.

**Why this priority**: PRD §17.4, and the input §44A.15 needs.

**Acceptance Scenarios**:

1. **Given** venues with known depth, **When** depth at each band is reported, **Then** each venue is measured by its own executable-depth measure.
2. **Given** a fixed notional, **When** the best execution venue is chosen, **Then** it is chosen by all-in cost, not by top-of-book price.
3. **Given** a venue whose top of book is best but whose all-in cost is not, **When** the best venue is chosen, **Then** the other one wins.
4. **Given** several venues, **When** concentration is reported, **Then** it rises as liquidity gathers in fewer venues.
5. **Given** a venue that cannot fill the notional, **When** the best venue is chosen, **Then** it is excluded and the exclusion is reported.

---

### Edge Cases

- What happens when every venue is stale? The consensus is refused, the same as for one venue — a consensus of nothing is not zero.
- What happens when two venues tie at the median of an even count? The median is their mean, and the result says the count was even, so a reader knows the figure is interpolated rather than observed.
- What happens when a venue quotes a representation of a different asset? It is refused before the consensus is computed: the registry is what makes venues comparable, and comparing across assets is the mistake it exists to prevent.
- What happens when the best-execution notional is zero? Refused. Every venue's all-in cost is zero at zero size, so the answer would be arbitrary.
- What happens when concentration is asked of one venue? It is the maximum, which is correct — one venue holds all of it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The consensus mid MUST be the median of the contributing venues' normalized mids, and the result MUST name the contributors.
- **FR-002**: A venue whose mid is missing, or older than a configurable staleness tolerance at the instant, MUST NOT contribute, and the contributor count MUST be reported.
- **FR-003**: A consensus over fewer than two contributing venues MUST be refused.
- **FR-004**: Venues MUST be recognised as quoting one asset through the registry, never through tickers.
- **FR-005**: An even contributor count MUST be reported alongside the interpolated median.
- **FR-006**: `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)` MUST be computed for each contributing venue.
- **FR-007**: Mid-based basis MUST be refused when either side is an AMM.
- **FR-008**: `executable_basis_bps(N)` MUST be computed from each side's executable price at a caller-supplied notional, with no default notional.
- **FR-009**: Per-venue returns over 1, 5 and 10 second windows MUST use only prices at or before the instant.
- **FR-010**: Pairwise lagged correlations MUST be computed over aligned event-time windows.
- **FR-011**: Lead-lag outputs MUST declare themselves research-only, and no signal-path module may import the lead-lag module.
- **FR-012**: Depth per venue at 10/25/50 bps MUST use each venue's own executable-depth measure.
- **FR-013**: The best execution venue MUST be chosen by all-in cost, and a venue that cannot fill the notional MUST be excluded and reported.
- **FR-014**: Liquidity concentration across venues MUST be reported.
- **FR-015**: Every output MUST be computed from data available at the instant asked about.
- **FR-016**: No module may consult a system clock.

### Key Entities

- **Venue quote**: one venue's mid and the instant it was observed.
- **Consensus**: the agreed mid, who contributed, and how many.
- **Execution comparison**: what a given size costs on each venue, all in.
- **Lead-lag observation**: returns and correlations, marked research-only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The consensus matches a hand-computed median, and names its contributors.
- **SC-002**: A stale or missing venue is excluded and the count reflects it.
- **SC-003**: Fewer than two contributors refuses.
- **SC-004**: Venues quoting different representations of one asset are comparable; venues quoting different assets are refused.
- **SC-005**: Basis matches the formula, and is zero at the consensus.
- **SC-006**: Mid-based basis refuses for an AMM; executable basis at a notional does not.
- **SC-007**: Returns and correlations use only data at or before the instant.
- **SC-008**: No signal-path module imports the lead-lag module, verified over the source.
- **SC-009**: The best execution venue is chosen by all-in cost, demonstrated on a case where top-of-book and all-in disagree.
- **SC-010**: Concentration rises as liquidity gathers in fewer venues.
- **SC-011**: No module references a system clock.

## Assumptions

- **No second CEX connector.** No work package builds one; Binance and Uniswap v3 are the venue pair, and quotes are supplied to the engine rather than fetched.
- **§17.1's volume/depth weighted median is not built**; the PRD marks it experimental.
- **Executable prices are supplied per venue**, computed by REQ-WP-004's `depth_within_bps` for a book and REQ-WP-015's `depth_to_bps` for an AMM. This engine compares them; it does not reimplement either.
- **No trading rule derived from lead-lag**, per FR-011 and PRD §17.2.
