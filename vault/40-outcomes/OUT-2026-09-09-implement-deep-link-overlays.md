---
id: OUT-2026-09-09-implement-deep-link-overlays
step: implement
records: [REQ-US-002]
commit: null
---

## What was done

The alert's link carries PRD §27.2's active layers, and the chart opens centred
on the signal's own bar drawing exactly those. 6 link tests, 16 web tests.

This closes REQ-US-002, whose acceptance had two clauses and whose first was
only half met: the instant was parsed and marked, and then the view was fitted
to the whole loaded history.

## A clamp that was never the thing holding the range

The sweep found one survivor: removing the upper clamp on the visible range
changed nothing. With a sixty-bar window and twenty-bar fixtures the lower clamp
already held the range inside the data, so the upper one was never what stopped
it running past the end. A history shorter than the focus window — a new
listing, or the start of a backfill — is the case that separates them, and it is
now a test.

## What was decided

- **A partly-readable overlay list is discarded whole** ([[ADR-045]]), extending
  [[ADR-020]] to a parameter that can fail halfway. The page states which of the
  three restoration states it is in.
- **An empty list is restored exactly.** `overlays=` says no layers were on;
  falling back to defaults would overrule a recorded fact with a guess.
- **A duplicate is drawn once.** Sloppy is not corrupt.
- **One alert is one link**: the set is sorted and deduplicated before
  serialization, so a resent alert does not look like a different signal.

## Mutation results

Nine mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An alert with no overlays writes a default set | `test_an_alert_declaring_nothing_omits_the_parameter` |
| The overlay order is the tuple's | `test_the_overlay_order_is_stable` |
| An unreadable list is partly restored | `overlays.test.ts` — discards an unrecognised list |
| An absent parameter is treated as restored | `overlays.test.ts` — not recorded |
| An empty list falls back to the defaults | `overlays.test.ts` — recorded-and-empty |
| Duplicates are kept | `overlays.test.ts` — drawn once |
| The range is not centred | `overlays.test.ts` — centred on the bar |
| An out-of-range instant centres on nothing | `overlays.test.ts` — whole history |
| The range runs past the data | `overlays.test.ts` — short history |

## What is still open

- **Nothing populates `Alert.overlays`.** Alerts sent today land in "not
  recorded", which the page says out loud.
- **The chart draws six of the twelve layers.** The vocabulary is the full list,
  so links stay valid as the rest arrive.
- **The two vocabularies are kept in step by hand.** A rename on one side turns
  every link unreadable; [[ADR-045]] records that as a gap rather than a fix.
