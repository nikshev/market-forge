---
id: OUT-2026-09-09-implement-setup-families
step: implement
records: [REQ-US-005]
commit: null
---

## What was done

`channelflow.backtest.families` and `SignalMachine.opens`: each setup family
backtestable on its own, its report naming it and carrying its thresholds. 12
tests.

This closes REQ-US-005.

## Two fixtures that agreed with the wrong code

The sweep found two survivors, and both were the fixture's fault rather than the
test's.

**A falling channel only ever opens shorts.** So a restriction matching the
boundary alone — letting `middle_continuation_short` open middle-zone *longs* —
behaved identically to the real one on every existing fixture. The mirror
fixture, a climbing channel whose middle zone opens longs, is where the two
differ.

**`upper_rejection_short`'s zone equals the engine's own default.** A family
whose zone was quietly dropped ran on the default zone, which was the same zone,
so nothing moved. A narrower zone and a wider one, compared against each other,
are what make the zone observable.

Both are the same shape as the day's earlier finds: a property that holds, over
a fixture that cannot tell whether it holds.

## An interference test that measured two things

The first version compared `UPPER_REJECTION_SHORT`'s run against an unrestricted
one and expected more candidates. It failed — the family also raises the quality
floor from the engine's 0.5 to PRD §31's 0.70, so the run opened fewer. The test
now uses a family whose thresholds match the default machine, so the only
difference between the two runs is which setups may open.

## What was decided

- **The restriction is a machine field, not a report filter.** Filtering leaves
  each family's count depending on the other family's setups, because the engine
  tracks one candidate at a time.
- **`opens=None` is every pair**, so the runner without a family is byte-for-byte
  the engine [[REQ-WP-010]]'s parity test compares against.
- **A family is data**, asserted by a test over the module's own source.

## Mutation results

Nine mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| The open restriction is ignored | `test_the_other_family_runs_on_the_same_bars_and_sees_its_own` (+1) |
| The restriction matches on boundary alone | `test_a_family_restricts_direction_as_well_as_zone` |
| The family's machine is not used | `test_neither_familys_count_depends_on_the_others_setups` (+1) |
| The report forgets its family | `test_the_report_names_the_family` |
| The family's thresholds leave the configuration | `test_the_familys_thresholds_are_in_its_report` |
| An inverted zone is accepted | `test_an_impossible_zone_is_refused` |
| The family's zone is not applied | `test_the_familys_zone_is_what_the_machine_uses` |
| The family's quality floor is not applied | `test_the_familys_thresholds_are_in_its_report` |
| `upper_rejection_short` loses the PRD's numbers | `test_upper_rejection_short_carries_the_prds_own_numbers` (+1) |

## What is still open

- **No CLI.** PRD §38's `channelflow backtest --strategy upper_rejection_short`
  is unbuilt and uncovered by any requirement; this is what it would call.
- **No economic metrics**, unchanged: [[ADR-009]] still holds, and a family run
  reports signal quality only.
