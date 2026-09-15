---
id: REQ-NRT-REPAINT
title: Repaint regression over a stream of stored channel snapshots
type: constraint
prd_ref: "§35.3"
prd_lines: "4870-4877"
phase: null
status: implemented
depends_on: [REQ-WP-006]
tags: []
hard_gated: true
---

## Requirement

PRD §35.3, quoted in full — the section calls it the *critical test*:

> **Critical test:**
>
> 1. Feed bars one at a time.
> 2. Store channel snapshots.
> 3. Continue feeding future bars.
> 4. Assert all previous snapshots unchanged.

**The token is a word, not a letter.** `REQ-NRT-A` through `REQ-NRT-F` are
§13A.28's six named tests, "Test A" to "Test F". This is a different section, and
lettering it `G` would claim §13A.28 has a seventh test it does not.

### What already holds, and why it is not this

`tests/unit/channels/test_no_lookahead.py::test_appending_future_bars_does_not_change_a_past_snapshot`
fits `RollingOLSChannel` at one moment, appends future bars, **refits the same
moment**, and demands the same answer. That proves the fit is a function of its
prefix — a real property, and the one [[REQ-WP-006]] was written for.

It is **one model at one moment**, and four models exist: `RollingOLSChannel`,
`HuberChannel`, `QuantileChannel`, `KalmanChannel`. That is the gap.

### Two hypotheses that did not survive measurement

Both are recorded because each would have justified a stronger claim than the
evidence supports, and because leaving them unwritten invites re-investigation.

**"A model could mutate a snapshot it already handed out."** Measured:
`ChannelSnapshot` is a frozen pydantic model whose every field is immutable by
type — `int`, `str`, `float`, `tuple`, and a frozen `ChannelQuality`. There is no
list and no dict to reach into. Plain assignment raises `ValidationError`. Only
`object.__setattr__` gets through, which no ordinary code path does by accident.
So storing the snapshots rather than refitting guards a route that is nearly
closed already. Worth closing — it costs a deep copy — but it is not the reason
this requirement exists.

**"A stateful model answers differently warm than cold."** `KalmanChannel`
carries filter state by design, so a model fed one bar at a time seemed likely to
answer at `t` differently from one fitted cold at `t`, which a refit test could
never see. Measured over 120 bars, feeding forty of them one at a time before
asking: **all four models answer identically warm and cold**, `KalmanChannel`
included. The hypothesis was wrong for every current implementation.

### So what this requirement actually is

A guard on future code, in the same sense as [[REQ-WP-072]]'s: the properties
hold today and **nothing keeps them holding**. A fifth model, or a change that
makes `KalmanChannel` genuinely incremental, would break §35.3 with only a
one-model one-moment test watching. §35.3's procedure — every model, every moment
in a stream, comparing what was stored rather than what can be refitted — is what
notices.

## Acceptance

- Bars are fed **one at a time**, and a snapshot is taken and retained after
  each. Not a refit: the object handed out earlier is the object checked later.
- After every subsequent bar, **every** previously stored snapshot is compared
  against what it was when it was stored, and must be unchanged.
- The comparison is by value over the whole snapshot, not over a chosen field. A
  check that compared only the centre would pass a model that repainted a band.
- It runs for every channel model, enumerated mechanically from the package, so
  a model added later without this test is a red suite rather than an omission.
- A model that deliberately mutates a stored snapshot is caught and named —
  proven by a test that introduces exactly that fault and watches the suite fail.
- The suite needs no services and no network.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-114-repaint-and-leak-suites]]
- **Tests:**
    - `tests/unit/channels/test_repaint_regression.py::test_a_model_that_edits_what_it_handed_out_is_caught`
    - `tests/unit/channels/test_repaint_regression.py::test_a_mutation_of_only_the_latest_snapshot_is_caught_too`
    - `tests/unit/channels/test_repaint_regression.py::test_a_repainting_model_is_caught_and_named`
    - `tests/unit/channels/test_repaint_regression.py::test_a_retained_entry_keeps_a_copy_that_is_not_the_snapshot`
    - `tests/unit/channels/test_repaint_regression.py::test_a_snapshot_field_added_later_is_compared_too`
    - `tests/unit/channels/test_repaint_regression.py::test_each_moment_is_refitted_by_a_fresh_model`
    - `tests/unit/channels/test_repaint_regression.py::test_equality_is_by_value_not_by_identity`
    - `tests/unit/channels/test_repaint_regression.py::test_every_channel_model_is_covered`
    - `tests/unit/channels/test_repaint_regression.py::test_no_snapshot_changes_once_the_future_exists[HuberChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_snapshot_changes_once_the_future_exists[KalmanChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_snapshot_changes_once_the_future_exists[QuantileChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_snapshot_changes_once_the_future_exists[RollingOLSChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_stored_snapshot_is_mutated[HuberChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_stored_snapshot_is_mutated[KalmanChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_stored_snapshot_is_mutated[QuantileChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_no_stored_snapshot_is_mutated[RollingOLSChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_the_replay_examines_every_moment[HuberChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_the_replay_examines_every_moment[KalmanChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_the_replay_examines_every_moment[QuantileChannel]`
    - `tests/unit/channels/test_repaint_regression.py::test_the_replay_examines_every_moment[RollingOLSChannel]`
- **Code:**
    - `src/channelflow/channels/repaint.py`
- **Outcomes:** [[OUT-2026-09-15-implement-repaint-regression]], [[OUT-2026-09-15-spec-repaint-and-leak-suites]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.
