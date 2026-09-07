---
id: OUT-2026-09-07-implement-domain-model
step: implement
records: [REQ-WP-002]
commit: null
---

## What was done

All 16 tasks. Nine models across five modules under `src/channelflow/domain/`,
27 domain tests, seven committed fixtures. `mypy --strict` passes over 8 source
files with no ignores. Full suite 178 green.

**RED first:**

```
$ pytest tests/unit/domain/ -q
ERROR tests/unit/domain/test_round_trip.py
E   ModuleNotFoundError: No module named 'channelflow.domain'
```

**The guard that matters, proven by mutation.** Disabling the integer-to-string
encoding produced:

```
AssertionError: timestamp drifted by -64 ns; it must not be encoded as a JSON number
```

That is the failure the specification was written around, reproduced on demand.

## What was decided

- **A real bug, caught by the round-trip test rather than by review.** Book
  levels are tuples, so the containing model stays immutable — and the encoder
  handled `dict` and `list` but not `tuple`, so `Decimal` values inside a book
  reached `json.dumps` raw and raised. Two of the seven fixtures could not even
  be generated. Fixed, with the reason recorded at the line: the test found what
  reading the code did not.
- **Every integer is encoded as a string, not just timestamps.** Block numbers,
  sequences, `sqrt_price_x96` and tick values are all ordering-critical, and
  `sqrt_price_x96` in the fixture is 4.3e27 — far beyond a double. Special-casing
  only `event_time_ns` would have left the same hazard elsewhere under a
  narrower name.
- **Fixtures use fixed values, never `now()`.** A fixture that changes with the
  clock is not a fixture. The timestamp is deliberately above 2^53 so every
  regeneration re-proves the JavaScript-safety property.
- **`--regenerate-fixtures` is a deliberate switch.** Regenerating is sometimes
  right; doing it silently is not. The failure message says every stored event
  changes shape, because that is what a changed encoding means.
- **`extra="forbid"` on every model.** A venue that adds a field must not have
  it silently swallowed — the connector should fail and be updated on purpose.

## What is still open

- **`market_type` remains a free string**, as the spec's Assumptions said. The
  first connector needing a fixed vocabulary should propose one.
- **No persistence.** These models are shapes that survive a round trip; PRD
  §29's storage schemas are a separate concern behind adapters.
- **The extremum and signal models of §13A.19 and §21 are untouched**, as scoped.
- **Fixture placement.** These are per-model; PRD §35.2 describes end-to-end
  raw-to-signal fixtures. They may want to live together eventually.
