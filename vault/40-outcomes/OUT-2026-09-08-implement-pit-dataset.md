---
id: OUT-2026-09-08-implement-pit-dataset
step: implement
records: [REQ-WP-017, REQ-BIAS-001, REQ-BIAS-003, REQ-BIAS-004, REQ-BIAS-007, REQ-BIAS-008, REQ-BIAS-010]
commit: null
---

## What was done

`channelflow.dataset`: PRD §24.2's as-of join, §23.5A's labels from
REQ-WP-019's confirmed extrema, §24.3's purged chronological folds, §42's
point-in-time universe, and a leakage checker. 37 tests.

Six `hard_gated` anti-bias rules move to `implemented`. Five stay at `draft`,
each named in [[ADR-024]] with the reason.

## What was decided

- **The leakage checker takes a protocol, not `Row`.** `Row` refuses every
  violation at construction — `model_construct` included, since pydantic still
  runs `model_post_init` — so a checker that only accepted `Row` could never be
  handed a violation. It would have been untestable in the way that looks like
  it works. That is not a workaround: rows will arrive from Parquet, from a
  database, from a later implementation of this module, and none of those
  routes runs the constructor. The protocol is the checker saying so.
- **Every refusal is a named reason, counted separately.** The join has five
  ways to decline a row. A build returning an empty list for all five would
  make "we have no data here" and "our dataset is contaminated" the same
  result.
- **A tie the data cannot break is refused.** Two snapshots with the same
  `as_of_ns` and the same `source_max_event_ns` are indistinguishable; picking
  one would make the dataset depend on list order.
- **`NO_TURN` is available at the horizon's end**, not at `t`. "Nothing turned
  in this window" is knowable only once the window has passed.
- **The label window is `(t, t + H]`.** An extremum at `t` itself belongs to
  the previous row's horizon; counting it in both would double-label the turn.

## A fixture that left a rule with nothing to look at

`test_a_clean_dataset_passes_and_says_what_it_examined` failed on its own
`examined` counts: the fixture's rows all carried `NO_TURN` labels, so the
`label_available_at_confirmation` rule examined zero rows and the assertion
that every rule saw something was false.

The checker was right and the fixture was thin — which is exactly the silent
non-coverage [[ADR-025]] added the `examined` counts to make visible, catching
it on the first run rather than after someone wondered why a rule had never
failed. The fixture now labels every fourth row with a turning point.

## Mutation results

Seven mutations, all caught, every restore verified against its backup:

| Mutation | Caught by |
| --- | --- |
| The join takes the latest snapshot regardless of `t` | `test_only_snapshots_at_or_before_t_are_joined` (+3) |
| A missing snapshot is forward-filled | `test_a_missing_snapshot_drops_the_row_and_is_counted` (+1) |
| The label is available at the extremum, not the confirmation | `test_a_labels_availability_is_the_confirmation_time_not_the_extremum` |
| The purge is dropped | `test_a_horizon_that_purges_everything_is_refused` (+1) |
| The locked test split is readable | `test_the_test_split_is_locked_until_explicitly_unlocked` |
| An empty dataset reports clean | `test_an_empty_dataset_fails_rather_than_passing_clean` |
| An unfinalized bar is accepted | `test_a_feature_from_an_unfinalized_bar_is_refused` (+1) |

The third is the one the task file singled out, and it behaved as predicted: a
one-word change, no error anywhere, and a dataset whose labels are available
before the market could have known them.

## What is still open

- **PRD §41 rules 2, 5, 6, 9 and 11 stay at `draft`** ([[ADR-024]]). Rule 2 is
  the one worth watching: REQ-NRT-D enforces it for the extrema engine and
  nothing enforces it generally, and marking it implemented on one engine's
  guard would put a false edge in the graph.
- **No storage.** §24.1's table is unbuilt; the row shape matches its columns
  so persistence later is a change of source, not of meaning.
- **§23.5B's regression targets** — bars to next extremum, next extreme
  return, quantiles — are not built. §23.5A's classification is.
- **Nothing consumes this yet.** REQ-WP-018's GMDH and REQ-WP-019's remaining
  two acceptance criteria are what it was built for.
