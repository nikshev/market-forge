---
traces: [REQ-BT-001]
status: draft
---

# Feature Specification: Signal outcomes, fill models and economic metrics

**Feature Branch**: `bt-001-outcomes-economics`

**Created**: 2026-09-09

**Input**: REQ-BT-001 — PRD §40, §25.4, §25.5 and §41 rule 9. Extracted because
[[ADR-009]] named these as what would lift its restriction, and nine of the
seventeen experiments are waiting on it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Say what happened to a signal, including "we cannot tell" (Priority: P1)

Each signal gets an outcome over its horizon: target, stop, timeout, or
ambiguous.

**Why this priority**: PRD §40's own emphasis — "never choose the favorable
ordering". A bar that reaches both the target and the stop is the single place a
backtest can flatter itself without anyone noticing, because both orderings are
plausible and only one is profitable.

**Acceptance Scenarios**:

1. **Given** price reaching the target and never the stop, **When** the outcome is resolved, **Then** it is `target` and the first touch time is recorded.
2. **Given** price reaching the stop first, **When** it is resolved, **Then** it is `stop`.
3. **Given** neither touched by the horizon, **When** it is resolved, **Then** it is `timeout` and the horizon return is reported.
4. **Given** one bar whose range contains both the target and the stop, **When** it is resolved, **Then** it is `ambiguous`.
5. **Given** an ambiguous bar, **When** the outcome is read, **Then** neither a target nor a stop time is claimed.
6. **Given** a horizon extending past the available bars, **When** an outcome is requested, **Then** it is refused.

---

### User Story 2 - Enter at a price someone could have got (Priority: P1)

Market-at-next-bar-open, or market-at-signal-close with slippage.

**Why this priority**: §25.4 lists both for phase 1, and the difference between
them is most of the difference between a backtest and a fantasy — a fill at the
signal's own close is a fill at a price that was already gone.

**Acceptance Scenarios**:

1. **Given** a signal and a following bar, **When** the next-open fill is used, **Then** the fill is that bar's open.
2. **Given** no following bar, **When** the next-open fill is used, **Then** it is refused rather than falling back to the close.
3. **Given** a long signal and slippage, **When** the close fill is used, **Then** the fill is above the close.
4. **Given** a short signal and slippage, **When** the close fill is used, **Then** the fill is below the close.
5. **Given** the phase-2 models, **When** fills are described, **Then** they are named as unbuilt.

---

### User Story 3 - Report economics only with costs in them (Priority: P1)

Every §25.5 economic metric, computed after fees and slippage, with the costs
reported beside them.

**Why this priority**: §41 rule 9 states it as a rule, and [[ADR-009]] explains
the failure it prevents: a gross win rate is quoted as the win rate, because the
caveat does not travel with the number.

**Acceptance Scenarios**:

1. **Given** resolved outcomes and a cost model, **When** metrics are computed, **Then** win rate, returns, expectancy in R, profit factor, Sharpe, Sortino, maximum drawdown, MFE, MAE and target-hit probability are reported.
2. **Given** no cost model, **When** metrics are requested, **Then** they are refused.
3. **Given** a cost model, **When** the metrics are read, **Then** the fees and slippage applied are reported with them.
4. **Given** ambiguous outcomes among the inputs, **When** metrics are computed, **Then** they are excluded and counted.
5. **Given** one set of outcomes, **When** metrics are computed twice, **Then** the results are equal.
6. **Given** a set with no resolved outcome, **When** metrics are requested, **Then** they are refused rather than reported as zeros.

---

### Edge Cases

- What happens when a bar's low is exactly the stop? It is a touch. A backtest that requires a strict breach is choosing the favourable ordering by a tick.
- What happens when the target is hit on the fill bar itself? It counts, provided the fill happened before it — with a next-open fill, that bar's own range applies from the open onward.
- What happens when every outcome is ambiguous? The metrics are refused, and the ambiguous count says why. A profit factor over nothing is not zero.
- What happens when the costs exceed every gross return? Every metric is negative and reported. That is a result, and it is the one §41 rule 9 exists to make visible.
- What happens to the maximum drawdown of a single trade? It is that trade's own loss, or zero. Defined for one, not only for many.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An outcome MUST carry every field §40 lists, and MUST be separate from the signal.
- **FR-002**: `outcome` MUST be one of `target`, `stop`, `timeout`, `ambiguous`.
- **FR-003**: A bar containing both the target and the stop MUST resolve to `ambiguous`.
- **FR-004**: An ambiguous resolution MUST NOT claim either touch time.
- **FR-005**: A touch MUST include equality with the level.
- **FR-006**: `mfe_pct` and `mae_pct` MUST be measured from the fill price over the horizon.
- **FR-007**: An outcome MUST be refused when the horizon extends past the bars.
- **FR-008**: Market-at-next-bar-open MUST use the following bar's open, and MUST be refused when there is none.
- **FR-009**: Market-at-signal-close MUST apply configurable slippage against the trade in both directions.
- **FR-010**: §25.4's phase-2 fills MUST be named as unbuilt.
- **FR-011**: Every economic metric MUST be computed after fees and slippage.
- **FR-012**: An economic metric requested without a cost model MUST be refused.
- **FR-013**: The costs applied MUST be reported with the metrics.
- **FR-014**: Ambiguous outcomes MUST be excluded from economic metrics and counted.
- **FR-015**: Metrics over no resolved outcome MUST be refused.
- **FR-016**: Metrics MUST be deterministic.
- **FR-017**: No module may consult a clock.

### Key Entities

- **Signal outcome**: §40's record.
- **Fill**: a price and the model that produced it.
- **Cost model**: fees, slippage, funding and gas.
- **Economic report**: §25.5's metrics, the costs, and the excluded count.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Each of the four outcomes is produced by a constructed case.
- **SC-002**: A both-touched bar is ambiguous and claims no times.
- **SC-003**: A touch at exactly the level counts.
- **SC-004**: A horizon past the data refuses.
- **SC-005**: Next-open fills at the next open, and refuses without one.
- **SC-006**: Slippage moves a long fill up and a short fill down.
- **SC-007**: Metrics without a cost model refuse.
- **SC-008**: Metrics match hand-computed values on a constructed set.
- **SC-009**: Costs are reported with the metrics, and raising them lowers expectancy.
- **SC-010**: Ambiguous outcomes are excluded and counted.
- **SC-011**: No resolved outcome refuses.
- **SC-012**: No module references a clock.

## Assumptions

- **Targets and stops are supplied.** The signal engine produces them (`invalidation_price`, `research_target_price` on an alert); resolving an outcome is not the place to invent either.
- **Funding cost and DEX gas are cost-model fields, applied when supplied.** §25.5 lists them "where applicable", and a venue with neither passes zero rather than having the fields absent.
- **R is measured against the initial risk** — the distance from fill to stop — which is what "expectancy in R" means and what makes it comparable across setups.
