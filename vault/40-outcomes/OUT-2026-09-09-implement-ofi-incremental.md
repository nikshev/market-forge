---
id: OUT-2026-09-09-implement-ofi-incremental
step: implement
records: [REQ-EXP-004]
commit: null
---

## What was done

`channelflow.research.ofi_incremental` and `channelflow.channels.features`:
EXP-004's five cumulative arms, the increments between them, and PRD §19's
registration for the channel's own numbers. 17 tests.

## A registry that was empty until something imported it

The first run of `available_from_registry` reported four channel features and
nothing else — no OFI, no depth imbalance, no walls. The registry fills as its
producing modules are imported, and reading it cold sees only what happened to
be loaded already.

Inside the test suite the fault is invisible: other test files import those
modules, so by the time this test runs the registry is complete. It shows only
in a fresh process, and one test now runs one.

That is the second time today a green suite hid something because the suite
itself supplied the missing condition.

## A vacuous assertion

The sweep found `all(name.startswith("ofi_") for name in found["ofi"])` passing
over an empty tuple. A membership rule matching nothing satisfied the shape
assertion while emptying the arm it defines. Non-empty is now asserted first.

## What was decided

- **Both taxonomies refuse the other's families.** EXP-004's finer slicing is
  not a superset of REQ-US-006's vocabulary, and an arm that could name either
  would measure a group its own experiment does not define.
- **The increment's sign is stated and tested.** Lower Brier is better, so an
  improvement is negative — reversed, the one family that worked reads as the
  one that hurt.
- **An increment over an unscored arm is absent.** "This family added nothing"
  and "there was nothing to add it to" are different findings.

## Mutation results

Ten mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The arms are not cumulative | `test_every_arm_is_scored_on_the_same_folds` (+1) |
| An increment over an unscored arm is zero | `test_an_increment_over_an_unscored_arm_is_absent_not_zero` |
| The increment is taken the other way round | `test_a_family_that_helps_moves_the_increment_the_right_way` |
| The added features are not computed | `test_each_increment_names_what_it_added` |
| The registry is read cold | `test_the_families_resolve_in_a_process_that_imported_nothing_else` |
| The family membership loses a prefix | `test_the_families_are_resolved_from_the_registry` |
| An arm's taxonomy is ignored | `test_an_arm_naming_a_family_outside_this_taxonomy_is_refused` (+1) |
| The taxonomy defaults to anything | `test_the_us_006_taxonomy_still_refuses_this_ones_families` |
| The channel features are not registered | the registry gate, by name |
| The position ignores a zero-width channel | `test_a_channel_with_no_width_has_no_position` |

## What is still open

- **The DEX families are still empty**, which is why [[REQ-EXP-007]]'s arms will
  report as not run when it is built.
- **Nothing runs this on real data.** The experiment is the procedure; the
  dataset is [[REQ-WP-017]]'s and the venue data is unbuilt.
