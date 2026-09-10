# Phase 0 — Research

## 1. Which stop does the policy see?

**Decision**: the decided stop, not the active one.

**Rationale**: a live engine knows what it asked for. Shown the active stop, the
policy re-proposes the same movement at every point until the acknowledgement
lands — inflating the update count, burning the cooldown, and producing reason
histograms that describe an engine with amnesia rather than a market with
latency. The distinction being modelled is precisely that these two are
different, so collapsing them anywhere defeats the feature.

The trigger is the other half: it is evaluated against the **active** stop,
because that is the one the exchange would have executed.

## 2. What resolves the tie at the acknowledgement instant?

**Decision**: at exactly `t + L` the update is not yet effective.

**Rationale**: §44A.27 forbids resolving ordering by outcome, so the rule has to
be fixed in advance and stated where it is applied. The conservative reading is
the one that does not credit the position with protection it may not have had —
so the old stop applies at the tie.

Checkable, per SC-004, by two paths on which the rule pays in opposite
directions: it must resolve both the same way. An implementation choosing by
outcome fails that; one that merely happens to be conservative passes, which is
the correct standard, because motive is not testable and behaviour is.

## 3. What is the default, and where does the number come from?

**Decision**: 160 ms, all of it on the network/exchange leg.

**Rationale**: it is the gap in §44A.27's own example — signal computed at
`.100`, acknowledgement at `.260` — which measures exactly that leg. The
decision and computation legs are real and have no figure anywhere in the PRD;
they default to zero and the total is documented as a **floor**, not an
estimate. Inventing plausible values for them would put a number that looks
measured where an honest floor belongs.

**Alternatives considered**: defaulting to zero. Rejected by the requirement:
every caller who did not think about it would get the optimistic case, and the
optimism would look like a result.

## 4. Do the naive baselines wait too?

**Decision**: yes.

**Rationale**: they send stop updates. A baseline obeyed instantly while the
adaptive policy waits is not a comparison of policies, and the difference it
reports would be partly the latency the two were given.

## 5. Why does this not move any existing result?

**Decision**: verified, not assumed.

**Rationale**: existing paths step a minute at a time and the default is 160 ms,
so every decision is active by the next observation. The 20 existing replay
tests running unchanged is the evidence; if one moves, the default is reaching
past the example it came from.
