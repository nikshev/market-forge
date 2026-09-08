---
id: OUT-2026-09-08-implement-chart-and-read-api
step: implement
records: [REQ-API-001, REQ-WP-009]
commit: null
---

## What was done

`channelflow.api`: PRD §28's endpoints over repository protocols, with §27.5's
two channel modes and §28.7's WebSocket. `apps/web`: the chart, the mode
control, the load states and the deep-link parser. 30 Python tests, 19
TypeScript tests.

The deep link REQ-WP-008 has been emitting since this morning now has a page to
open.

## What was decided

- **The chart's decisions were extracted from the chart.** `lightweight-charts`
  needs a laid-out container and jsdom has none, so a component test can never
  see a candle. `series.ts` holds what to draw — which candles, which lines,
  which bands, where the marker sits — and is tested directly. Testing the
  component instead would have asserted its props while rendering nothing.
- **`toSeconds` returns the library's `Time`, not `number`.** The library
  accepts seconds, business days or date strings, and would plot nanoseconds in
  the year 58,000 with no error and an empty chart. Its own type is what stops
  a caller passing them; a mutation feeding nanoseconds fails two tests.
- **The mode is sent explicitly in both directions**, never omitted for the
  default. An omitted parameter relies on the server's default staying right,
  and [[ADR-020]] wants both ends stating the same thing.
- **The refit relies on REQ-WP-006's own guard.** `fit` is called with the
  requested instant as `as_of`, so the API cannot leak the future even if a
  handler were written carelessly — the same argument REQ-WP-010's backtest
  runner rests on.
- **Zones are drawn as price lines, not filled areas.** The library has no band
  primitive; faking one with stacked areas would put a shape on the chart whose
  edges do not mean what they look like.
- **`outcome` is its own field from the first commit**, always null today
  ([[ADR-010]]). PRD §27.4 requires the later outcome to be separable from what
  was known at signal time, and retrofitting that separation is how it gets
  lost.

## Mutation results

Nine mutations, all caught:

| Mutation | Caught by |
| --- | --- |
| `as_seen_then` defaults to false | `test_the_parameter_defaults_to_as_seen_then` (+2) |
| AS-SEEN-THEN quietly refits when nothing is stored | `test_as_seen_then_is_never_reconstructed_after_the_fact` |
| The bars query drops its end bound | `test_bars_honour_the_time_range` |
| A snapshot stored later becomes eligible | `test_a_snapshot_taken_after_the_instant_is_not_returned` |
| The subscription ignores its channel filter | `test_only_subscribed_channels_are_delivered` (+1) |
| The deep link defaults to the refit | `test_it_opens_AS-SEEN-THEN_by_default` (+1) |
| The chart drops its mode label | `says which mode is showing` (+1) |
| Candles are fed nanoseconds | `produces one candle per bar` (+1) |
| An absent channel draws a flat one | `draws no channel and no zones when there is none` |

The first two are the ones the task file predicted would matter, and both
behave as predicted: each returns a perfectly plausible channel, and every
alert already sent carries a link that would then open a refit.

## A restore that did not restore

Mutation M9 was reverted with `git checkout -- src/series.ts`, which failed
silently in the shell's output stream: the file was untracked, so there was
nothing to check out and the mutation stayed in place. The final run caught it
— one test still failing after "restore" — and it was undone by hand. The
lesson is the same as REQ-WP-011's stale-bytecode one: a mutation harness must
verify its own restore, not assume it.

## What is still open

- **`min_score` and `setup_type` filters are unimplemented**; both need PRD
  §43's ranker. They remain in REQ-API-001's text as what is owed.
- **The API is in-memory** ([[ADR-019]]). A restart loses everything; nothing
  populates the repository from a running pipeline yet.
- **No authentication.** Not exposed publicly in this phase.
- **§27.2's other overlays, §27.3's lower panes and §27.4's explanation panel**
  are out of scope by REQ-WP-009's acceptance criteria.
- **`main.tsx` and the Vite config now carry markers**, so R8 is satisfied for
  the frontend half.
