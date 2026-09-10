# Phase 1 — Data model

Two events and two counters. No new tables.

| Event | Carries | Published when |
|---|---|---|
| `ExtremumObserved` | `candidate` | a running high or low is noticed |
| `ExtremumConfirmed` | `extremum` | a reversal crosses its threshold |

`Recording` gains `confirmed_extrema` and `extremum_candidates`, and its
`skipped` tally now covers four recorders rather than two. Two tests enumerate
every term of that sum rather than checking a lower bound — with `>=` the
channel snapshots alone satisfied it, and a dropped term went unnoticed.
