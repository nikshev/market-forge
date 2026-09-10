# Contract — the positioning readings

```
long_short_ratio(states, *, at_ns, staleness_ns) -> float | None
top_trader_ratio(states, *, at_ns, staleness_ns) -> float | None
long_short_z(states, *, at_ns, window=20, staleness_ns) -> ZScore
top_trader_z(states, *, at_ns, window=20, staleness_ns) -> ZScore
```

## Guarantees

- `None` means the venue published nothing. It is never 1.0, never 0.0, and
  never a sentinel that survives arithmetic.
- A ratio of zero or below cannot exist: `DerivativesState` refuses it.
- No state later than `at_ns` enters any reading or any history.
- A z-score is over exactly `window` readings, or it is refused with the count
  it found. It is never a shortened window reported as a full one, and never
  zero standing in for "nothing to say" ([[ADR-026]]).
- States that published no ratio are not observations.
- Freshness is measured on the newest published reading. `StaleState` when it is
  older than `staleness_ns`; `NoStateAvailable` when there is no state at all.
- The two ratios are independent: one may be present while the other is absent,
  and neither is derived from the other.

## Does not

Fill the fields. Which venue endpoint feeds which ratio belongs with the
connector; this carries and reads them, as with every other derivative feature.
