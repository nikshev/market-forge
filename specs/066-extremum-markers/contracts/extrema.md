# Contract — extrema

```
GET /api/v1/extrema?instrument_id&timeframe_ns[&as_of_ns]
extremumMarkers({ confirmed, candidates, mode, atNs }) -> ExtremumMarker[]
```

## Guarantees

- `as_of_ns` is a **knowledge** filter: a confirmation appears only when
  `known_at_ns <= as_of_ns`, a candidate only when `observed_at_ns <= as_of_ns`;
- the boundary is inclusive;
- a returned confirmation reports `extremum_time_ns` unchanged — where the turn
  was, not when it was confirmed;
- omitting `as_of_ns` returns everything on record, which is what `CURRENT
  REFIT` asks for;
- a candidate named by a shown confirmation's `source_candidate_id` is not drawn
  again;
- an unconfirmed candidate is still drawn.

## Does not

Re-derive an extremum, decide a threshold, or filter by window. A window is a
separate question and both filters apply independently.
