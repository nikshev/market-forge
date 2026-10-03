---
id: OUT-2026-10-03-plan-no-unfinalized-upsample
step: plan
records: [REQ-NRT-UPSAMPLE]
commit: null
---

## What was done

Planned the seam as `specs/125-no-unfinalized-upsample/` and — because the requirement is
`hard_gated` — wrote the tests first and ran them against the unchanged code.

**RED, as run** (`tests/unit/test_upsample_seam.py`, 11 tests, kept out of `tests/` until the
implementation exists because a red suite cannot be committed):

    4 failed, 7 passed
    AssertionError: a bar computed from four of five minutes          (minutes 0,1,2,3,3)
    assert 'duplicated' in 'window 0 at 5m has 6 of 5 source 1m bars' (six bars for five minutes)
    assert (Bar(venue='binance', ... is_final=True),) == ()           (one source bar not final)
    assert ['complete', ..., 'one not final'] == ['complete']         (five shapes: three give a bar)

The seven that pass are guards and say so: the complete-window control, the existing
missing-minute and open-window behaviour, nothing readable as of seven instants inside a window and
readable at its close, and no bar closing after `t` over a day at every configured timeframe — plus the control
that a read ignoring `as_of_ns` does meet future bars, so that property check can fail.

## What was decided

- **Identify, don't count.** `resample` judged a window complete by `len(window) != expected`.
  The plan identifies the minutes: missing, duplicated and not-final each refuse the window.
  Rejected: dropping the bad bars and folding the rest (the silent skip the requirement forbids),
  raising (a refusal is the channel the pass already prints), deduplicating in `read_bars` (hides
  the case and changes every other reader), a consumer-level test (no such consumer exists).
- **`planned` was skipped, and why.** R5 forbids a status past `specified` without a linked test;
  the tests cannot be committed red. The requirement stays `specified` through the plan and task
  commits and reaches `tested` in the commit that turns the suite green, which is where `CLAUDE.md`
  says the rung is recorded anyway. The RED output above is the proof the tests came first.
- **The refusal keeps its shape.** `present` becomes the distinct count and the reason keeps its old
  prefix and appends what was wrong, so the existing assertions hold untouched.
- **A mutation sweep is part of the work, not an afterthought**: two specs, one for `resample.py`
  and one for the `bars` schema's as-of column (`close_time_ns` → `open_time_ns` would return every
  open window to every as-of reader and nothing notices today).

## What is still open

- **The tests take 160 s; the spec allows 60.** The day fixture is built and resampled twice. The
  tasks make one stored fixture per module and measure the instants; if it cannot be brought under
  the budget the spec's SC-004 changes, with the reason, rather than the test being thinned silently.
- **A different-process finding, not this change's:** someone staged `README.md` in the repository
  while this was being planned. Commits here name their paths so it is not swept in.
