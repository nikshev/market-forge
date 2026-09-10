---
id: OUT-2026-09-10-implement-long-short
step: implement
records: [REQ-WP-031]
commit: null
---

## What was done

Two optional ratios on `DerivativesState`, four readings in
`derivatives/positioning.py`, three registrations with null policies. 16 tests,
every gate clean, 7 of 7 mutants caught after the sweep.

[[REQ-WP-031]] moves to `implemented`, which closes [[REQ-PHASE-3]]'s last
deliverable.

## What the sweep found

Four mutants died against the first test set. Three survived, and all three were
in `_z`:

- **freshness measured on the newest state instead of the newest published
  reading**;
- **freshness not checked at all**;
- **the history reading past the instant asked about**.

One cause: the z-path had no freshness test of any kind, and no look-ahead test.
Every existing test passed `NOT_ABOUT_FRESHNESS` and a history ending at the
instant, so the two clauses that make the reading honest were executed by every
test and asserted by none.

The first two matter for the same reason the whole requirement does. A venue
that keeps sending states and stops sending positioning is stale in exactly the
way the rule exists to refuse — and measured against the state it reads as
current while the connector's health looks fine. That is absence wearing a
value's clothes one level up from the field itself.

The third is Principle I, and it was unasserted in a module whose history is
built by hand. It is now asserted the way the silent-states test is: twenty
readings before the instant and twenty after, with a window of 40 that can only
be filled by reading the future. A window of 20 would have passed either way.

## What is still open

- **Nothing writes positioning**, as nothing writes the other derivative
  features. Named in the spec, not discovered here.
- **The connector field mapping is undecided** — which venue endpoint feeds
  which ratio. Deliberately outside this requirement.
- **The staleness tolerance is the shared default** (5 minutes). Venues publish
  positioning on their own cadences, and a per-venue tolerance is a real question
  that nothing yet forces an answer to.
