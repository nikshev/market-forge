---
id: OUT-2026-09-08-spec-derivatives
step: spec
records: [REQ-WP-013, REQ-BIAS-005]
commit: null
---

## What was done

`specs/016-derivatives/spec.md`: five user stories, 13 functional requirements,
8 success criteria, two ADRs.

## What was decided

- **A z-score refuses rather than returning zero** ([[ADR-026]]). Zero is the
  most meaningful value a z-score can take — "exactly average" — so a feature
  returning it whenever it has nothing to say will read as a calm market to
  every consumer. Both degenerate cases refuse: too few observations, and a
  zero standard deviation.
- **The price/OI regime is a label nothing acts on** ([[ADR-027]]). PRD §16.2
  says so itself: "stored as feature, not hard-coded trading truth". The four
  names are kept verbatim, including the word "candidate" in each, which is the
  PRD hedging its own matrix — and which survives copy-paste into a dashboard
  where "new shorts" alone would read as a fact.
- **Funding's settlement boundary is what closes REQ-BIAS-005.** A rate is for
  the interval *ending* at `next_funding_time`, so before that it is an
  estimate the venue may revise; features at `t` use only intervals that have
  closed.
- **§16.5's long/short ratios are not built.** The PRD calls them optional and
  requires them labelled provider-specific; with one provider the label would
  be the only content.

## What is still open

- **Cross-venue dispersion** (§16.1, §16.3) is REQ-WP-016; the DEX comparison
  is REQ-WP-014/015.
- **Predicted funding is passed through, not modelled.**
