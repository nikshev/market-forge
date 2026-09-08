---
id: OUT-2026-09-08-implement-evm-connector
step: implement
records: [REQ-WP-014, REQ-BIAS-006]
commit: null
---

## What was done

`channelflow.chain`: PRD §18.3's raw envelope, §18.4's finality ladder and
reorg model, §18.6's versioned decoder registry, §18.17's provider pool. 27
tests, no network.

REQ-BIAS-006 moves to `implemented`. Ten of PRD §41's eleven anti-bias rules
are now closed; only rule 2 (centered filters in live features, enforced for
one engine and not generally) and rule 11 (discarded experiment variants)
remain.

## A leftover mutation was found in committed-shape source

`ledger.py`'s never-regress guard read `if False:` when this session resumed.
It was a mutation from an interrupted sweep in the previous session, and it
survived because that session's process was killed between the mutation and
its restore.

Two things caught it, in this order: the finality test failed, and a grep for
`if False:` / `if True:` across `src`, `tools` and `apps/web/src` found exactly
one occurrence. That grep is now the habit — a mutation harness that can be
killed needs a sweep afterwards, not only a restore inside it.

The previous session's own notes had already recorded the two weaker versions
of this lesson: REQ-WP-009's `git checkout` on an untracked file that silently
did nothing, and REQ-WP-018's mutation that hung the suite instead of failing
it. This is the third, and the strongest: a mutation can outlive the process
that made it.

## What was decided

- **Provider health is windowed, not lifetime.** Found by a test that expected
  a cooldown to expire and watched the provider stay unhealthy for ever: with
  lifetime rates, one error puts a provider permanently above any threshold and
  the cooldown can never help. On a long-running process one bad hour would
  poison a week.
- **The ledger owns availability and reorgs together**, because they are the
  same question asked twice — what was knowable at an instant.
- **`Finality` is an `IntEnum`**, so `status >= Finality.SAFE` reads as PRD
  §18.4 rule 2 states it.
- **The record validates its own time ordering**, so no read has to defend
  against a record that claims to have been available before it was observed.

## Mutation results

Seven mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| `as_of` filters on block time instead of availability | `test_a_record_is_invisible_until_it_was_available` |
| A reorg deletes rather than orphans | `test_a_reorg_orphans_a_record_and_never_edits_it` (+1) |
| A finalized block may be reorganised | `test_a_finalized_block_cannot_be_reorganised` |
| Finality regresses | `test_finality_never_regresses` |
| A mismatched ABI hash decodes anyway | `test_a_mismatched_abi_hash_fails_closed` |
| An unhealthy provider is returned | `test_no_healthy_provider_refuses` (+2) |
| A disagreement is resolved silently | `test_a_cross_provider_disagreement_is_reported_not_resolved` |

The second is the one the task file singled out: stamping `orphaned_at` with
zero rather than the reorg's instant removes the record from every read,
including reads of instants before the reorg — and it looks like correct
cleanup.

## What is still open

- **Protocol adapters** (§18.7 to §18.11) are REQ-WP-015 and beyond.
- **§18.5's discovery registry** is not built; pools are supplied.
- **No provider implementation ships.** The protocol is defined and the adapter
  is owed, behind the same boundary [[ADR-012]] and [[ADR-018]] drew.
- **§18.20's data-quality state machine** exists only as the finality status.
