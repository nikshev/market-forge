---
id: OUT-2026-09-09-implement-repaint-comparison
step: implement
records: [REQ-US-003]
commit: null
---

## What was done

`channelflow.api.comparison` and `GET /api/v1/channels/comparison`: the stored
snapshot at an instant beside a refit over history up to a later one, every
delta measured, the hindsight span stated. 13 tests.

This closes REQ-US-003.

## Reading the section against the code

The interesting part of this one was not the implementation. `api/channels.py`
already served both of PRD §27.5's views, and its `CURRENT REFIT` caps every fit
at the requested instant — the right default for an endpoint a chart calls.

But §27.5 claims the distinction "directly exposes repaint-like differences",
and two views of one information set expose model drift, not repaint. REQ-US-003
says "the model's **later** state" in as many words. The gap was in what the
code measured, not in whether it worked.

[[ADR-046]] records the decision to let this refit see later bars, and the three
things that keep it from becoming a leak: the span is stated in nanoseconds, the
payload declares itself research-only, and no signal-path module may import the
module at all.

## A test that was checking a word

The import ban first scanned each module's whole source for "comparison" and
failed immediately: `alerting/dedupe.py` and `stops/replay.py` both use the word
in prose. Narrowed to import lines — which is the actual prohibition. A check
that fails on a docstring gets renamed around rather than fixed, and then checks
nothing.

## Mutation results

Seven mutations, all caught on the first sweep, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The inverted-hindsight guard is dropped | `test_a_later_instant_that_is_earlier_is_refused` |
| The refit is capped at the compared instant | `test_the_comparison_carries_both_channels_and_their_difference` |
| The hindsight span is always zero | `test_the_hindsight_span_is_stated` |
| A zero width divides anyway | `test_a_zero_width_channel_reports_no_ratio_rather_than_infinity` |
| The difference is taken the other way round | `test_the_comparison_carries_both_channels_and_their_difference` |
| `research_only` defaults to false | `test_every_comparison_declares_itself_research_only` |
| The stored snapshot is a refit too | `test_a_zero_width_channel_reports_no_ratio_rather_than_infinity` |

The second is the one the requirement is about: capped at the compared instant,
the endpoint returns two plausible channels and measures nothing.

## What is still open

- **No chart view.** The acceptance asks that the snapshot be available for
  comparison, and it is; showing the two side by side on the chart is separate
  work.
- **The package list in the import ban is maintained by hand**, the same open
  edge [[ADR-040]] carries.
