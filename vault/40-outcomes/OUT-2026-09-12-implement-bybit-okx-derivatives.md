---
id: OUT-2026-09-12-implement-bybit-okx-derivatives
step: implement
records: [REQ-WP-049]
commit: null
---

## What was done

`tools/record/derivatives_capture.py`, one fixture covering both venues in a
single pass, `derivatives_state` on Bybit's and OKX's normalizers, two mutation
specifications. 36 tests, 18 of 18 mutants caught.

Phase 5 now has four venues producing `DerivativesState` — Binance, HyperCore,
Bybit, OKX — which is what funding dispersion needed and did not have.

## Two disagreements, both measured, both quiet

**Open interest is contracts on OKX and base units on Bybit.** Read naively,
OKX appears to hold **51.5 times** Bybit's BTC open interest; read correctly it
holds **0.52 times**. The error is exactly the contract value, so it is a
hundredfold on BTC and tenfold on ETH — which is why the test asserts the
invariant rather than a threshold. The first attempt did assert a threshold,
tuned to BTC, and ETH failed it.

This is [[REQ-WP-044]]'s contract-size trap again, now in a field nothing else
cross-checks. OKX does publish `oiCcy` already in base units, and the module
uses it while checking it against `oi × ctVal` — a cross-check the venue gives
away for free, and a disagreement means the contract value in hand is not the
one the venue applied.

**`OKX.fundingTime` is `Bybit.nextFundingTime`.** The same instant under
opposite names, measured to the same millisecond, and OKX's own
`nextFundingTime` is the settlement eight hours after. A connector matching
field names puts one venue a period out, and a dispersion across that boundary
compares a settled rate against a forthcoming one.

After normalization the two venues agree to the nanosecond, and that equality is
the single assertion this requirement stands on.

## A third thing, found while writing it

**OKX's `premium` is not the basis.** It looks exactly like one. Checked against
the index endpoint: the two are **0.14 basis points** apart, because the premium
is averaged over a funding window and the basis is instantaneous.

Substituting it would have removed a fourth HTTP call and compared OKX's window
against Bybit's instant under one name. The specification carries a prohibition
rather than only a requirement, because the tempting wrong answer is right
there in a response already being parsed.

## Four readings are not a snapshot

Bybit answers with one call and one timestamp. OKX needs four, so a state is
stitched from readings taken moments apart — 738 milliseconds in the capture.

The spread is carried rather than discarded, and a state whose readings are
further apart than a caller-supplied bound is refused. The bound has no default,
for the reason [[REQ-WP-039]]'s retention policy has none: how stale is too
stale is a property of what the state is for.

The state is stamped with its **oldest** reading. A state is no fresher than its
stalest part, and stamping it with the newest would claim a freshness none of it
has.

## The harness earned its keep twice on its first day

**It refused an unexplained survivor.** `absent funding becomes zero` survived
on the OKX side: the absent-is-not-zero rule was tested for Bybit and not for
OKX, which is a separate code path. A real gap, found because a survivor without
a recorded reason now fails the sweep.

**It caught a drifted pattern.** `ruff format` collapsed the basis expression
onto one line, and two mutations stopped matching. Under the old scratch scripts
that was a printed `SKIP` that scrolled past; now it is a failure that names the
two mutations and says the source moved.

## What is still open

- **Funding dispersion itself**, which now has four venues to disperse across.
- **The shared session layer**, which Phase 5's acceptance also asks for:
  reconnect, keepalive and rate limits, and today only Binance has one.
