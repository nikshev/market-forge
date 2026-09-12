---
id: REQ-WP-050
title: Funding dispersion compares rates over a common interval or refuses
type: work-package
prd_ref: "§16.1, §17, §45 Phase 5"
prd_lines: "2464-2471, 2560-2576, 6831"
phase: 5
status: implemented
depends_on: [REQ-WP-049, REQ-WP-016]
tags: []
---

## Requirement

PRD §16.1 lists "cross-venue funding dispersion" among the derivatives features,
and §45's Phase 5 lists it as a deliverable. Four venues now publish funding
([[REQ-WP-049]]) and nothing disperses it.

**The rates are not comparable as they arrive**, and this is the whole
requirement. Measured from each venue's own funding history on 2026-09-12:

    Hyperliquid   60 minutes
    Binance      480 minutes
    Bybit        480 minutes
    OKX          480 minutes

A Hyperliquid rate is an **hourly** rate; the other three are eight-hourly. Put
side by side without normalising, the four differ by a factor of eight before
the market has said anything, and a dispersion computed over them measures the
settlement schedule rather than the market. The number is positive, ordered and
believable, and it moves when funding moves — so it looks like a signal and
behaves like one.

**The interval must be observed, not assumed.** Eight hours is the common case
and is exactly why a default would be dangerous: it would be right for three
venues, silently wrong for the fourth, and wrong again for the next venue that
settles hourly. A venue whose interval nobody has established is refused rather
than assumed.

**Staleness excludes, it does not carry forward.** Phase 5's acceptance says so
for consensus mid and the same applies here: a venue whose last funding reading
is older than the tolerance is excluded with a reason, because a stale rate
reused as a current one narrows the dispersion by pretending a venue agrees.

**One venue is not a dispersion.** [[REQ-WP-016]]'s consensus refuses a median
over a single venue — "that venue's mid wearing a better name" — and the same
holds here.

## Acceptance

- Rates are normalised to a caller-supplied common interval before anything is
  compared, and the normalisation has no default interval.
- A venue whose funding interval is not supplied is refused, not assumed.
- The measured intervals are carried in a fixture, derived from each venue's own
  funding history rather than stated, and a test shows one venue differs from the
  rest by a factor of eight.
- A dispersion computed on raw rates is shown to differ materially from one
  computed on normalised rates, on real data.
- A stale venue is excluded with a reason recorded, never carried forward.
- A dispersion over fewer than two contributing venues is refused.
- The result names its contributors and its exclusions, in the shape
  [[REQ-WP-016]]'s `Consensus` established.
- A venue that publishes no funding is excluded rather than counted as zero.
- No test opens a socket.

## Notes

Human territory. Never machine-rewritten.

**Annualising is deliberately not the interface.** A per-year figure is the
conventional way to compare funding and it bakes in a choice — 365 days against
360, compounding against simple — that belongs to whoever is reading the number.
The interface normalises to an interval the caller names, and annualising is
then one call with one argument.

**What "dispersion" means is not stated by the PRD**, so this reports three
things rather than choosing one: the median, the spread between the extremes,
and the standard deviation. They answer different questions — where the middle
is, how far apart the ends are, and how tightly the venues cluster — and a
single number would hide which was meant.

**Sign matters and is preserved.** Funding is signed by nature, and a dispersion
over absolute values would call a market where two venues pay longs and two pay
shorts "tight".
