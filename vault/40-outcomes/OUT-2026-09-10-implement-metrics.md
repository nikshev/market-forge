---
id: OUT-2026-09-10-implement-metrics
step: implement
records: [REQ-WP-036]
commit: null
---

## What was done

`channelflow/metrics.py`: a registry, a Prometheus text renderer, two
derivations over data the system already produces, and `UNIMPLEMENTED` naming
the nine §33 metrics nothing here writes. 18 tests; 16 of 16 mutants caught
after the sweep, plus one recorded as equivalent.

RED first: the test module failed to import what it was testing.

## What the sweep found

Fourteen mutants died against the first test set. One survived, and it was the
same species as [[REQ-WP-035]]'s: **a branch that could not be reached.**

`render` skipped a metric whose series was empty. Nothing could produce one:
`observe` used `setdefault` and then always assigned, and the only refusal after
that point — a counter going backwards — required a prior sample, so the series
was never empty when it ran.

The fix is not a test for the branch. `observe` now builds the series and
assigns it only once a reading exists, which removes the window the branch was
guarding, and the branch is gone. Two tests assert the property both were
reaching for: a refused observation leaves the exposition byte-for-byte
unchanged, and no `# TYPE` line ever appears without a sample beneath it.

**One mutant is recorded as equivalent**: putting `setdefault` back changes no
behaviour, because the guard it races with cannot fire on an empty series. It is
noted rather than chased, since the difference is two spellings of one
behaviour, not a missing assertion.

That makes twice in two requirements that the sweep found a guard rather than a
gap. Both times the branch was the symptom and the invariant was the fix, and
both times the branch had been written from habit — the shape of a defensive
check, with nothing behind it.

## What was decided while building

- **Registering creates no series.** The whole requirement is this one
  behaviour, and it is the opposite of what nearly every metrics library does.
  A test asserts that a registry holding registered metrics and no observations
  renders the empty string.
- **`UNIMPLEMENTED` carries a reason per entry**, and a test asserts none is
  blank — otherwise the list decays into a TODO. A second test asserts nothing
  derived appears in it, so it cannot drift into naming something that grew a
  producer.
- **No client library**, as planned: a global registry, a `/proc` collector and
  a clock are three things this codebase has spent requirements removing.

## What is still open

- **Nine of §33's eleven metrics have no producer**, named in `UNIMPLEMENTED`
  with the reason. That is the requirement's answer, not a gap in it.
- **Nothing serves the exposition.** Where the text is scraped from is a
  deployment question, and deployment is a separate Phase 8 deliverable — so
  "monitoring dashboards" stays in `not_delivered`, with this half done.
