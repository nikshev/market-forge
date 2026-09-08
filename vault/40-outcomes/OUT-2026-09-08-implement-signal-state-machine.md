---
id: OUT-2026-09-08-implement-signal-state-machine
step: implement
records: [REQ-WP-007]
commit: null
---

## What was done

All 13 tasks. Three modules under `src/channelflow/signals/`, 16 tests, 245 in
the suite, `mypy --strict` clean over 24 source files.

## A gap in my own specification, found by a test

The spec said "at most one candidate per symbol and timeframe" and never said
**when a new one may open after a terminal one**. So a candidate expired while
price still sat in the zone, the next bar opened a fresh candidate, that expired
too — an endless carousel producing a new candidate every few bars from the same
unchanging price action.

Found because a test expected an expired candidate and got a freshly opened one.
Fixed by adding FR-018 and SC-009 to the specification, not by patching the code
quietly: price must leave every zone before a new candidate may open.

## An ordering defect that would have silently lost signals

Expiry was checked before progression, so a candidate expired on the very bar
that would have confirmed it. `expiry_bars` means "that many bars *without*
confirmation" — and a bar that confirms is not one of them. Expiry now runs
last, and only when the bar advanced nothing.

This one is worth noting because it fails quietly: nobody would have seen a
missing signal, only a slightly lower confirmation rate that looked like the
market.

## The three mutations

| Mutation | Caught by |
|---|---|
| allow any transition — skip steps | `test_an_illegal_move_is_refused_rather_than_performed` |
| drop the channel-quality precondition | `test_a_low_quality_channel_opens_nothing` |
| let a terminated candidate reopen in-zone | `test_an_expired_candidate_does_not_revive`, and one more |

## What was decided

- **One transition table, not four.** ADR-008: direction and boundary are
  candidate attributes. Adding a family adds preconditions, not states, and
  determinism stays provable over one table.
- **Every move goes through `_advance`**, which refuses anything the lifecycle
  does not list. That makes "no skipped steps" a property of the code rather
  than a habit of whoever wrote the branches.
- **`CandidateState` is a `StrEnum`.** ruff pointed out the `str, Enum` idiom is
  superseded on 3.11+; adopted rather than silenced.
- **A confirmation that happened stays recorded.** If price invalidates
  immediately afterwards, the confirmed transition remains in history and the
  candidate then resolves — PRD §0.5.

## What is still open

- **Three of PRD §21.3's four rejection detectors**, and all of §21.4's
  confirmation features. They need order-flow work not yet built. FR-013 makes
  them additions, proven by a test that registers a second detector.
- **Families E and F**, scoped out by ADR-008.
- **Scoring (§22) and alerting (REQ-WP-008)** are neighbours, not content.
- **Persistence.** §21.2 says to persist transitions; they are produced as
  immutable records and storing them is later work.
