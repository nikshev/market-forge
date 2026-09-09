# Acceptance criteria for the six unspecified experiments

**Date**: 2026-09-09
**Requirements**: REQ-EXP-003, -004, -005, -006, -007, -010
**Status**: derived and applied

## Why this document exists

Six of the seventeen `REQ-EXP-*` notes carry the `ACCEPTANCE-NOT-SPECIFIED`
marker. The PRD describes what each experiment compares and, for two of them,
what question it answers — but states no conditions under which the experiment
counts as done.

The precedent is REQ-WP-016, whose criteria were derived from PRD §17 and
approved before the spec was written
(`2026-09-08-cross-venue-acceptance-design.md`). The same method is used here:
nothing is invented that the PRD does not imply, every criterion is checkable,
and where a choice existed it is named rather than buried.

## What all six have in common

Five of the six are comparisons — a list of variants, in the PRD's own words:

| Requirement | Variants |
| --- | --- |
| EXP-003 | wick only; close-back-inside; two-bar confirmation; order-flow confirmation |
| EXP-004 | channel only; +L1 imbalance; +multi-level imbalance; +OFI; +persistence/cancellation |
| EXP-006 | conditional outcomes by funding z-score, OI change, liquidation imbalance, basis |
| EXP-007 | CEX only; +DEX price divergence; +DEX depth asymmetry; +swap imbalance; +LP liquidity changes |
| EXP-010 | whether cross-venue divergence predicts, after latency and costs |

EXP-005 is a yes/no question rather than a list: "does boundary overlap with
VAH/VAL/HVN/LVN materially change target-before-stop probability?"

That shape gives four criteria every one of them needs, and they are the same
four the repository has already had to write three times — for [[REQ-US-006]]'s
ablation, [[REQ-EXP-001]]'s model comparison and [[REQ-EXP-002]]'s sweep:

1. **Every variant the PRD names appears in the report**, as a result or as a
   stated absence. A variant silently missing is one the conclusion never
   considered.
2. **A variant whose inputs do not exist is reported as not run, with the
   reason, and never scored.** Three of these six name features the registry
   does not carry yet. Scoring an unavailable variant reports the absence of
   data as the absence of value — a finding about the pipeline dressed as a
   finding about the market.
3. **Every variant is measured on the same data, the same folds and the same
   costs.** PRD's EXP-015 says it in the PRD's own words — "use strict ablation
   and same walk-forward folds" — and it is what makes a comparison one.
4. **The experiment can conclude that there is nothing here.** EXP-017 states
   this explicitly for its own subject; it is the honest default for all of
   them, and [[ADR-042]] already built the pattern: a research result that
   raises is a research result that blocks.

## The criteria, requirement by requirement

### REQ-EXP-003 — Rejection detector

PRD §21.3 lists the four detectors and says "implement multiple rejection
detectors as plugins". `RejectionDetector` is already that plugin point, and
`CloseBackInside` is the one built.

- all four detectors named in EXP-003 appear in the report;
- each is a `RejectionDetector` used by the production signal machine, not a
  copy of its logic — §25.2 forbids the second implementation;
- a detector whose inputs do not exist is reported as unavailable with the
  reason, and is not scored;
- for each detector, over identical bars and one split: confirmation count,
  median confirmation lag in bars, the share of confirmations later invalidated,
  and expectancy in R after costs out of sample;
- the report ranks by a declared rule and states that a detector may win on lag
  and lose on expectancy;
- deterministic.

**What this deliberately does not require**: that all four be *built*. EXP-003
is a comparison, and the honest result of comparing one built detector against
three unbuilt ones is a report naming three as unavailable — which is what the
second common criterion is for.

### REQ-EXP-004 — OFI incremental value

The five arms are cumulative, and [[REQ-US-006]]'s ablation machinery already
runs exactly this shape.

- the five arms appear, cumulative as the PRD lists them: each contains the
  previous one's features;
- an arm whose family contributes no feature is reported as not run;
- all arms share one fold set and one target;
- the report says what each family added over the arm before it, rather than
  only each arm's absolute score;
- deterministic.

### REQ-EXP-005 — Volume profile confluence

The one yes/no question. "Materially" is the word that needs a definition, and
the definition has to be stated rather than chosen after seeing the answer.

- the two populations are defined point-in-time: setups whose boundary overlaps
  a VAH/VAL/HVN/LVN level at signal time, and those whose boundary does not;
- target-before-stop probability is computed for each from [[REQ-BT-001]]'s
  outcomes, with ambiguous outcomes excluded and counted;
- "materially" is a configured effect size, declared before the comparison and
  reported with the result;
- the answer is one of three — higher, lower, or not materially different — and
  the third is a real answer rather than a failure;
- a population too small to support the comparison refuses rather than
  reporting a difference.

### REQ-EXP-006 — Derivatives context

- outcomes are reported conditionally on each of the four variables the PRD
  names: funding z-score, OI change, liquidation imbalance, basis;
- each variable is bucketed by a declared rule, and the buckets are reported
  with their counts;
- a variable with no data is reported as unavailable, not as a flat conditional;
- every conditional uses the same outcomes and the same costs;
- the report distinguishes a conditional difference from a predictive one:
  contemporaneous conditioning is labelled as such, per EXP-014's own warning
  about confusing explanation with forecast value.

### REQ-EXP-007 — DEX incremental value

Same cumulative shape as EXP-004, over the DEX families and for ETH.

- the five arms appear, cumulative;
- an arm whose family contributes no feature is reported as not run — and today
  every DEX family is in that state, which is the honest report;
- all arms share one fold set;
- the report states the instrument it was run on, because EXP-007 names one.

### REQ-EXP-010 — Cross-venue lead/lag

PRD §17.2's prohibition governs this experiment: "do not convert correlation to
trading rule without OOS validation", and [[ADR-040]] already keeps the lead-lag
module off the signal path.

- predictive value is measured out of sample, not in the window the correlation
  was measured on;
- a latency is applied before any divergence is actionable, and it is a stated
  parameter rather than zero by default;
- costs are applied, per §41 rule 9;
- the experiment can conclude `NO_EDGE`, and does so when the out-of-sample
  result does not beat the no-skill baseline after latency and costs;
- nothing in the experiment's output is importable by the signal path — the
  import ban [[ADR-040]] established extends to it.

## What was chosen rather than derived

Three things. Each is a judgement, and each is stated in the requirement note so
a reader disagrees with the criterion rather than with a number:

1. **The metric set for EXP-003.** The PRD does not say what to compare
   detectors on. Confirmation count, lag, later-invalidation share and
   expectancy are chosen because they are the four things a detector can be
   wrong about: too few, too slow, too eager, or unprofitable.
2. **"Materially" as a configured effect size in EXP-005.** The alternative is a
   significance test, which needs a sample size no backtest here has yet.
3. **Latency as a required parameter in EXP-010.** The PRD says "realistic
   latency" without a number. A required argument with no default forces the
   caller to state theirs.
