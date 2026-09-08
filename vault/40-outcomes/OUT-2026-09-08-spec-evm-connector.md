---
id: OUT-2026-09-08-spec-evm-connector
step: spec
records: [REQ-WP-014, REQ-BIAS-006]
commit: null
---

## What was done

`specs/020-evm-connector/spec.md`: five user stories, 17 functional
requirements, 10 success criteria, two ADRs.

## What was decided

- **A reorg orphans, never deletes** ([[ADR-033]]). Deleting is the obvious
  implementation and it breaks replay parity: a strategy acted on a swap at
  12:00, the block was reorganised at 12:05, and a backtest over corrected data
  would never make that decision — which looks exactly like the strategy
  improving. PRD §41 rule 6 is the same rule from the research side, and its
  escape clause ("unless audit semantics explicitly allow it") is satisfied by
  keeping both the original and the invalidation.
- **Decoding fails closed; retention is unconditional** ([[ADR-034]]). PRD
  §18.6 rules out two failures in one sentence, and they pull opposite ways: a
  decoder matching on signature alone would decode an upgraded proxy into
  structurally valid, economically wrong events, while refusing the log
  entirely would lose the evidence needed to backfill once a decoder exists.
- **A finalized block cannot be reorganised.** Finality is the claim that this
  cannot happen; a chain contradicting it is a bug or an attack, and either way
  not something to absorb silently.
- **No network.** The provider protocol is defined and no implementation ships
  — the same boundary [[ADR-012]] and [[ADR-018]] drew.

## What is still open

- **Protocol adapters** (§18.7 to §18.11) are REQ-WP-015 and beyond; this
  supplies the registry they plug into.
- **§18.5's discovery registry** is not built: pools are supplied, not
  discovered.
- **§18.20's data-quality state machine** is not built beyond the finality
  status this feature needs.
