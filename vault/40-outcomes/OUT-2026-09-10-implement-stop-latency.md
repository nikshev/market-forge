---
id: OUT-2026-09-10-implement-stop-latency
step: implement
records: [REQ-WP-033]
commit: null
---

## What was done

`ActivationLatency` in `stops/replay.py`, the decided/active split inside both
run paths, `stop_updates_activated` on the outcome, and `latency` on the
comparison report. 15 new tests; 11 of 11 mutants caught after the sweep.

RED first: `test_latency.py` failed to import `ActivationLatency` — the honest
red for a value object that does not exist yet.

## The claim the plan said to verify

**Verified.** The 20 existing replay tests pass unchanged under the new
**default** latency, not under an opt-out: their paths step a minute at a time
and 160 ms never falls between two observations. That is the whole safety
argument for landing a behaviour change with a non-zero default, and it was
worth checking rather than asserting — if one of them had moved, the default
would have been reaching past the example it came from.

They now state `ActivationLatency.none()` where they build a report, which is
not a workaround: those tests were written against instantaneous activation, and
saying so is cheaper than a reader deducing that it did not matter.

## What the sweep found

Nine mutants died against the first test set. Two survived, and both were
assertions I had not written rather than code I had got wrong:

- **`stop_updates_activated` never incrementing.** The test for a latency longer
  than the path asserts the counter is zero, which a counter that never counts
  satisfies perfectly. The new test asks for the sentence the field exists for:
  two decided, one landed.
- **The walk measuring the decided stop.** §44A's median and 95th-percentile
  stop distances are quantiles of `stop_distances_r`, and measured against a
  stop the exchange had not yet obeyed they describe how close the position came
  to a level that was not protecting it. Nothing asserted which stop that
  distance was to.

Both are the same omission twice: a field added for a reason, with no test
naming the reason.

## What was decided while building

- **The noise buffer changes the numbers and not the argument.** The stop
  decided from an anchor at 99 lands at 98.85 — §44A.8's buffer, 1.5× the noise
  distance. The tests assert the buffered level and say why, rather than
  choosing anchors that make round numbers.
- **`ComparisonReport.latency` is required, not defaulted.** A defaulted field
  would state the wrong latency exactly as confidently as the right one.

## What is still open

- **Intra-bar trigger-versus-target ordering** remains unmet in its §44A.27
  form: a `PricePoint` carries one price, so the ambiguity cannot arise. Named
  in [[OUT-2026-09-10-spec-stop-latency]]; it needs an OHLC path model.
- **Decision and computation latency default to zero** because the PRD gives no
  figure. The total is a floor and says so in the docstring.
- **A rejected stop modification** is a different fact from a late one, and
  nothing here models it.
