---
id: OUT-2026-09-12-implement-funding-dispersion
step: implement
records: [REQ-WP-050]
commit: null
---

## What was done

`tools/record/funding_history_capture.py`, a fixture of four venues' settlement
history, `crossvenue/funding.py`, and a mutation specification. 29 tests, 17 of
17 mutants caught.

## The rates are not comparable as they arrive

Derived from each venue's own history:

    Hyperliquid    60 minutes
    Binance       480 minutes
    Bybit         480 minutes
    OKX           480 minutes

A Hyperliquid rate is **hourly** and the other three are eight-hourly. On the
captured readings, the raw spread across the four is 0.93 basis points and the
normalised spread is **1.44** — the raw figure understates disagreement by more
than a third, because the hourly venue's small number looks like agreement until
it is put on the same footing.

That is the whole requirement. The raw figure is positive, ordered, believable,
and it moves when funding moves. It looks like a signal and behaves like one,
which is the worst combination available.

**The interval is observed, never assumed.** Eight hours is the common case and
that is exactly why a default would be dangerous: right for three venues,
silently wrong for the fourth. The fixture carries *history* rather than a
stated interval — a stated one would have been a claim, and the claim would have
been wrong for one venue in four.

## Two things measured rather than reasoned about

**Staleness is one interval, and needs no constant.** A reading older than its
venue's own settlement period means the venue has settled again since, so the
rate in hand is not the rate in force. An hourly venue goes stale in an hour and
an eight-hourly one in eight; any fixed tolerance would be wrong for one of them.

**Normalisation is linear.** Funding accrues per period and is paid, not
reinvested, so eight hourly payments are eight times one. Compounding them would
model a position that rolls its funding back in, which is a different instrument
— and the test asserts the two differ rather than trusting the comment.

## A correction worth recording

Partway through I reported finding a systematic 1.7% bias: the derived interval
for Hyperliquid came out as 59 minutes rather than 60, and I was about to change
the estimator.

It was my own display arithmetic. `//60_000` on milliseconds truncates 59.998 to
59, and the venue's actual jitter is **two milliseconds**. Median, mode and mean
over the span all give 60.000 minutes. The estimator was right; the print was
wrong, and it is now rounded rather than truncated.

Checking before changing cost one command. Changing first would have replaced a
correct estimator to chase an artefact of a debug line.

## What the sweep found

Sixteen of seventeen died immediately. The survivor: taking the **first** gap
instead of the median as the interval.

Nearly equivalent, and not actually so. The regularity check tolerates five per
cent of jitter *by design* — Binance's own history is not exact — so a first gap
four per cent off passes it, and using that gap would put four per cent into
every rate normalised against that venue, in one direction. The test now uses a
history whose first gap is exactly that kind of outlier.

## What is still open

- **Whether the interval belongs on `DerivativesState`.** Today it is derived
  separately from history; carrying it with the rate would make the pairing
  structural rather than a caller's responsibility.
- **Phase 5's session layer**, which is now the phase's last item: reconnect,
  keepalive and rate limits for Bybit and OKX, where only Binance has one.
