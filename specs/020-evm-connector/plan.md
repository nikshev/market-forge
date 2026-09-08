# Implementation Plan: EVM connector

**Branch**: `wp-014-evm-connector` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/chain/`: PRD §18.3's raw envelope, the
append-only ledger that owns availability and reorgs, §18.6's decoder registry,
and §18.17's provider pool. No network anywhere.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new. `ChainDataProvider` is a protocol and no
implementation ships.

**Storage**: none. Records are in memory.

**Testing**: pytest, pure. Scripted fakes for decoders and providers.

**Target Platform**: `src/channelflow/chain/`.

**Constraints**: FR-002 (availability, never block time), FR-005 ([[ADR-033]]),
FR-010 ([[ADR-034]]), FR-016 (no clock, no socket).

**Scale/Scope**: 4 modules, 27 tests.

## Constitution Check

- **I (no look-ahead)** — FR-002 is the rule, and PRD §18.19's own example is
  the test: a backtest at 12:00:01.500 must not see a swap whose log completed
  at 12:00:02.250, however early its block time.
- **II (time is not one thing)** — a chain record carries four: block time,
  `observed_at`, `available_at`, `safe_at`. Conflating the first two is the
  mistake §18.19 exists to prevent.
- **III (history is immutable)** — §18.3 says raw chain records are immutable
  append-only data, and [[ADR-033]]'s reorg handling depends on it.
- **VII (live and replay are the same code)** — the envelope carries everything
  deterministic replay needs, which is §18.3's stated purpose.
- **XIV** — traces to REQ-WP-014 and REQ-BIAS-006.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/chain/
├── __init__.py
├── records.py    # §18.3's envelope, §18.4's finality ladder
├── ledger.py     # availability reads, finality advance, reorg orphaning
├── decoders.py   # §18.6's registry, fail-closed
└── providers.py  # §18.17's pool, health, cooldown, disagreement

tests/unit/chain/{test_ledger.py,test_decoders.py,test_providers.py}
```

**Structure Decision**: the ledger owns both availability and reorgs because
they are the same question asked twice — what was knowable at an instant. A
reorg changes the answer for instants after it and must not change the answer
for instants before it, and that is one rule, not two.

## Approach

**`Finality` is an `IntEnum`**, so `status >= Finality.SAFE` reads as PRD
§18.4 rule 2 states it. Ordering is the whole point of a ladder.

**The record validates its own time ordering.** A record whose `available_at`
precedes its `observed_at` cannot be constructed, so no read has to defend
against one.

**Provider health is windowed, not lifetime.** A lifetime rate on a
long-running process means one bad hour poisons a week.

## Complexity Tracking

> No violations.
