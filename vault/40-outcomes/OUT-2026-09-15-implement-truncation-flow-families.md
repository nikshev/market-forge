---
id: OUT-2026-09-15-implement-truncation-flow-families
step: implement
records: [REQ-NRT-LEAK]
commit: null
---

## What was done

Covered `trade_flow` (5) and `order_flow` (5) for PRD §35.4. **14 of 55**
features now have truncation cases; 41 remain in `NOT_YET_COVERED`.
[[REQ-NRT-LEAK]] stays at `tested`.

- `tests/unit/features/test_truncation_parity.py` — ten new cases, plus two
  tests that the inputs are not degenerate.
- `tests/mutations/truncation_boundaries.toml`, `tests/mutations/truncation_flow.toml`.

## What was decided

**Both families share one shape, and it is the shape the cases are built on.**
`FlowTracker` and `OFITracker` are stateful: observations go in, and
`window(window_ns, as_of_ns=t)` comes out. So the truncated run feeds a tracker
only events at or before `t`, the full run feeds it everything, and both ask for
the same window. That is the second family shape measured — the `channel` family
was "fit a model over a prefix or the whole series and read a field off the
snapshot".

**A test that the inputs are not degenerate.** Zero on both sides is agreement
about nothing happening. One case per covered family must produce a moving value,
or the series feeding it is flat and the parity it demonstrates is vacuous.

### Do these cases discriminate? Measured, and one answer was no

Seven boundary mutations were written against `ofi.py` and `flow.py` — each one
moving a window's edge so it reaches past `t`. Run against the truncation suite
**alone**, they catch **six of seven**.

The survivor is *"the window ignores its start"*, and it survives **correctly**.
Widening a window backwards does not reach into the future: the truncated run and
the full run change by the same amount and still agree. A truncation test is
blind to window-width errors by construction, and that is the right blindness —
§35.4 asks whether a value depends on data after `t`, not whether a window is the
length it claims. `test_ofi.py` owns that question and catches it, which is why
the committed specification lists both files.

Worth writing down because the opposite conclusion was available and wrong: a
survivor here looks like a weak assertion, and strengthening the truncation case
until it caught this would have meant testing something §35.4 does not ask about.

### Two corrections made during implementation

Both mine, both caught by the suite rather than by review:

- All five OFI cases failed on `AttributeError: 'OFIWindow' object has no
  attribute 'ofi'`. The field is `value`. For a moment this looked like five
  leaking features.
- `test_the_case_actually_computes_something` asserted `isinstance(value, float)`.
  The flow tracker returns `Decimal`. The assertion now accepts the numeric types
  and names the feature when it does not.

## What is still open

**41 features**: `derivatives` 19, `order_book` 15, `volume_structure` 5,
`defi` 2.

**The cost per case is now measured twice, not guessed once.** Two family shapes
so far, both cheap once the shape is known: four cases in one helper for
`channel`, ten in two for the flow families. `order_book` uses a `BookService`
and `derivatives` takes event lists with windows — closer to the flow shape than
to the channel one, on the evidence of their signatures, but that is still a
reading rather than a measurement.
