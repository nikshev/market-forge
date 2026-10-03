---
id: OUT-2026-10-03-implement-no-unfinalized-upsample
step: implement
records: [REQ-NRT-UPSAMPLE]
commit: null
---

## What was done

`resample` now **identifies** the minutes of a closed window instead of counting its bars, and
refuses the window when a minute is missing, appears twice, or is not final. One function changed
(`src/channelflow/pipeline/resample.py`, +50 −4); `Refusal` keeps its fields, `present` is the number
of distinct minutes held, and the reason keeps its old prefix and appends `; missing [..]`,
`; duplicated [..]`, `; not final [..]`, each capped at five open times and then `+N more`.
Eleven seam tests and one cap test are in `tests/unit/test_upsample_seam.py`; two mutation
specifications are in `tests/mutations/`. The 20 existing resample tests pass **unchanged**.

**RED, tests in `tests/`, source unchanged** (`.venv/bin/python -m pytest tests/unit/test_upsample_seam.py -q`):
`4 failed, 7 passed in 162.68s`.

- minutes 0,1,2,3,3: `AssertionError: a bar computed from four of five minutes`
- six bars for five minutes: `assert 'duplicated' in 'window 0 at 5m has 6 of 5 source 1m bars'`
- one source bar not final: `assert (Bar(venue='binance', … is_final=True),) == ()`
- the five window shapes: `assert ['complete', …, 'one not final'] == ['complete']` — three produced a bar

The seven that passed are guards and each says so: the complete-window control, the existing
missing-minute and open-window behaviour, nothing readable as of seven instants inside a window and
readable at its close, and no bar closing after `t` over a day at every timeframe.

**After.** `make test`: `3091 passed`. `make lint`, `make typecheck` clean. The four RED tests are
green; the cap test (`names_a_few_minutes_and_counts_the_rest`) was written alongside the change
and not before it, and says so.

**Differential on the live table** (T005; the deployed `resample`, still the old code, against the
new one on every one-minute series): 35 series × timeframe pairs, **18,026 windows judged**, bars
identical in 35 of 35, refusals identical in 35 of 35 (same windows, `expected`, `present`; the new
reason extends the old). Nothing on the deployment changes behaviour, as expected: it holds 55,840
one-minute rows and 55,840 distinct keys, and no unfinalized row.

**Mutation sweeps.** `resample_leak.toml` **8 caught, 0 survived**: the open window emitted; an
incomplete window folded anyway; completeness as a count again; a missing minute unnoticed; a repeated
minute unnoticed; a non-final bar folded; the refusal reporting every minute present; the refusal
naming every minute. `bars_as_of.toml` **1 caught, 0 survived**: the table's as-of column changed
from `close_time_ns` to `open_time_ns`, which would hand every window in progress to every as-of
reader. This is the evidence for "a deliberately leaking resampler is caught by the suite and
named": each of the nine is a leak, put in, and a test fails on it.

**The control that the property is the read's.** With `as_of_ns` deleted from the check, the same
loop finds **320,335** bars closing after `t` across 200 instants (T008), so the property test can
fail and is a statement about the read and not about the fixture.

**Time.** The eleven tests took 162 s against a 60 s budget. The cause was not the work but its
arithmetic: the instants list held **4,320** points, because every one of the 288 five-minute window
boundaries contributes three, at about twenty milliseconds a read, and the day's table was built
twice. It is now built once per module and the list holds **618**; the file runs in about 23 s.

## What was decided

- **The instants were reduced, in the spec and not only in the test.** The spec said every window
  boundary of every timeframe; 288 five-minute boundaries cost a minute of reads for nothing the
  others do not show, and the file's own docstring would have gone on claiming it. User Story 3 now
  says: every seventh minute, every boundary from fifteen minutes up, every fourth five-minute
  boundary. T007 asked for exactly this ("change SC-004 or the sentence, not thin it silently").
- **Status: `tested` and `implemented` in this one commit.** R5 forbids a status past `specified`
  without a linked test, and a test cannot be linked red; the RED output above is what proves the
  tests came first. Nothing in the acceptance needs a live service, so there is no later evidence to
  wait for, unlike [[REQ-WP-079]].
- **A refusal's size is capped.** One pass prints a `refused:` line per refusal (1,814 an hour on the
  deployment); a day window short of 1,439 minutes would otherwise carry 1,439 numbers.

## What is still open

- **Deployment (T013), on purpose.** The shared image rebuild recreates every service and would reset
  the 24-hour measurement of [[REQ-WP-079]] (from 07:18 UTC on 2026-10-03) and the `RestartCount` it
  asks for. Deploy after that check, then compare the resample log's `refused:` count with the
  1,814 an hour recorded before.
- **§13A.17's extrema hierarchy and confluence features** still have no requirement note and no code;
  the "consumer" half of this requirement is guaranteed on the read path until they do.
- **`read_bars` does not deduplicate.** `resample` no longer depends on that, but another reader of
  the table that assumes unique keys would meet a duplicate row as it is.
