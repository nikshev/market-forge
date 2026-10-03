# Implementation Plan: No unfinalized higher-timeframe close reaches a lower-timeframe consumer

**Branch**: `125-no-unfinalized-upsample` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/125-no-unfinalized-upsample/spec.md`

## Summary

Two of the spec's four stories need no new behaviour and one needs a small, exact one. The seam's
two halves — the as-of read filtering on `close_time_ns`, and "nothing computed at `t` reads a bar
closing after `t`" — already hold and have never been tested with a resampled bar; they become
guards. The behaviour that is wrong is in `resample`: it decides a window is complete by **counting**
its bars, so a repeated minute stands in for a missing one, and it never reads `is_final`. The plan
changes that one decision from a count to an **identification** of which minutes are present, how
often, and whether each is final, and then builds the part that makes a hard-gated constraint mean
something: a mutation sweep that puts each leak back and shows the suite catching it by name.

## What planning measured

**The tests are written and they fail for the right reasons.** Eleven tests were written first and
run against the unchanged code (`scratchpad/red_upsample.txt`): **4 failed, 7 passed**. The four are
the repeated-minute-with-a-gap window (one bar, no refusal), the non-final window (one bar, no
refusal), six bars for five minutes (refused today only because six is not five, with a reason that
says `6 of 5` and nothing about repetition), and the five-shape summary (three produce a bar). The
seven that pass are the control, the existing missing-minute and open-window behaviour, the as-of
read inside and at the close of a window, and the property over a day of bars. They are guards, and
each says so.

**They are too slow.** The eleven took **160 seconds**; the spec's SC-004 allows one minute. The cost
is the day-long fixture, written and resampled for every timeframe **twice** (once per
story-3 test) and read as of every chosen instant. Plan: store it once per module, and measure the
instants rather than guess them; the budget is a stated number the tasks check.

**The as-of column.** `bars`' schema declares `event_time_column="close_time_ns"`
(`tables/bars.py:72`), so `read_bars(as_of_ns=t)` is the storage layer's filter on close time. A
change of that one string to `open_time_ns` would return every in-progress window to every as-of
reader, and no test would notice today — which is the mutation story 4 includes.

**`read_bars` does not deduplicate** (it sorts every matching row by key), so a duplicate row in the
table reaches `resample` untouched. The live table has none (55,546 rows, 55,546 keys).

**No mutation specification exists for `resample.py`.** `tests/mutations/` has none for it, so the
requirement's last acceptance bullet — a deliberately leaking resampler is caught and named — has
never been proven by anything.

**No consumer reads two timeframes in one computation.** A search of `features/`, `models/` and
`channels/` finds no use of a second timeframe. The spec already states the property on the read
path for that reason; the plan keeps it there.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict` over `src/`

**Primary Dependencies**: pydantic `Bar`, pyiceberg tables through the existing `bars` table

**Testing**: pytest; the repo's mutation runner (`python -m tools.mutate`)

**Constraints**: no services, no network (FR-007); the whole suite for this requirement under 60 s (SC-004)

**Scale/Scope**: one pure function (`pipeline/resample.py`), one new test file, two mutation specs

## Constitution Check

| Principle | Result |
|---|---|
| I. No look-ahead | **This requirement is its seam between timeframes.** A bar built from four of five minutes, or from a minute that may still change, is a future close handed backwards. |
| III. History is immutable | **Holds, and is why it matters.** A higher-timeframe bar published early and later corrected would be a rewrite; the table has no way to say so. |
| VII. Live and replay are the same code | **Holds.** The resample job and a backtest fold with the same function. |
| XII. Correctness precedes performance | **Holds.** The identity check is O(window); no shortcut is taken. |
| XIV. Everything is traceable | Tests marked `REQ-NRT-UPSAMPLE`; `resample.py` carries the marker. |

Re-checked after design: no violations.

## Approach and what was rejected

**Chosen — identify, don't count.** For each closed window compute the expected set of source open
times (`s + k·source` for `k` in `0..expected-1`), then from the bars the window holds: which of those
are missing, which appear more than once, which are not final. Any of the three refuses the window.
`Refusal` keeps its fields; `present` becomes the number of **distinct** minutes present, and the
reason keeps its existing prefix (`window … has N of M source … bars`) and appends what was wrong:
`; missing [..]; duplicated [..]; not final [..]` with open times. The existing tests assert `present
== 4` and the window start in the reason, and both still hold.

**Rejected — drop non-final and duplicate bars quietly and fold the rest.** That is the silent skip
the requirement forbids: a correct bar and a bar computed from what remained look the same to a
reader.

**Rejected — raise.** A refusal is the channel the pass already prints and counts
(`refused: window … `); an exception would end a series' pass for a condition the requirement says
must be *visible and survivable*.

**Rejected — deduplicate in `read_bars` instead.** It would hide the case from `resample` and change
every other reader's answer; which of two copies is right is exactly what nothing here knows, so the
honest answer for the window is a refusal.

**Rejected — a consumer-level test.** No consumer exists. A test of one that does not exist would
bind nothing, so the guarantee is tested where it can be: the read.

**Rejected — mutation by hand, once.** The sweep is a committed file, so the claim "the suite sees
this violation" can be re-run, and a pattern that stops matching an edit is an error rather than a
silent pass.

## Tests (written first; RED recorded)

`tests/unit/test_upsample_seam.py`, 11 tests: **US1** control; repeated-with-a-gap; six-for-five;
non-final; missing (kept); open (kept); the five-shape summary. **US2** nothing readable as of any
instant inside a window (seven instants through the real table); readable at the close. **US3** a day
of bars at every configured timeframe, read as of every chosen instant, none closing late; and the
control that a read ignoring `as_of_ns` *does* meet future bars.

**Mutations** (`tests/mutations/resample_leak.toml`, `bars_as_of.toml`), written with the
implementation because their anchors are the new code: emit the open window; drop the completeness
check; count instead of identify; ignore finality; ignore duplicates; and, in the table's schema,
key the as-of read on `open_time_ns`.

## Project Structure

```text
specs/125-no-unfinalized-upsample/
├── plan.md  research.md  data-model.md  quickstart.md  tasks.md (not yet)
├── contracts/resample-seam.md   probe.py
src/channelflow/pipeline/resample.py            # the change
tests/unit/test_upsample_seam.py                # 11 tests
tests/mutations/resample_leak.toml  tests/mutations/bars_as_of.toml
```

## Why `planned` was skipped

`REQ-NRT-UPSAMPLE` is `hard_gated`: rule R5 forbids a status past `specified` without a linked test
in the repository. The tests exist and fail for the right reasons, but a red suite cannot be
committed (`make validate` and the hook run it), so they are not in `tests/` yet. The requirement
stays at `specified` through the plan and task commits and reaches `tested` in the same commit that
makes the suite green — which is where `CLAUDE.md` says the rung is recorded anyway. The RED
output is in the plan's outcome note, which is what proves the tests came first.

## Complexity Tracking

Empty.
