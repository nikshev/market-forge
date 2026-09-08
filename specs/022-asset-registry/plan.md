# Implementation Plan: Asset identity registry

**Branch**: `asset-001-registry` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Two modules under `src/channelflow/assets/`: PRD §18.13's entities, and the
registry that refuses everything §18.13 forbids.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new.

**Storage**: none.

**Testing**: pytest, pure. The fixture is PRD §18.13's own ETH example.

**Target Platform**: `src/channelflow/assets/`.

**Constraints**: FR-002 and FR-005 ([[ADR-038]]), FR-007 and FR-008
([[ADR-037]]), FR-014 (no clock, no socket).

**Scale/Scope**: 2 modules, 25 tests.

## Constitution Check

- **VI (every feature is documented)** — a mapping carries confidence and
  pricing source priority, both readable, so a consumer can say why it trusted
  a source.
- **X (thresholds are configuration)** — no thresholds here; the one constant,
  the wrapper depth bound, guards a malformed registry rather than a market
  decision.
- **XI (results are reproducible)** — the priority ordering is total and stable,
  so a consensus price built on it is reproducible.
- **XIV** — traces to REQ-ASSET-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/assets/
├── __init__.py
├── models.py    # §18.13's entities, with their invariants at construction
└── registry.py  # registration, resolution, and every refusal

tests/unit/assets/test_registry.py
```

**Structure Decision**: invariants that belong to one entity live in that
entity's `model_post_init` — a native marker and a contract address are mutually
exclusive whatever registry holds them. Invariants across entities, like a
dangling canonical asset, live in the registry, because only it can see both.

## Approach

**The fixture is the PRD's own example.** Native ETH, WETH on Ethereum, WETH on
Base and a Hyperliquid representation — so the test that matters most is a
direct reading of §18.13 rather than an invention.

**Every refusal has a test that constructs the violation.** The registry is
almost entirely refusals, and a refusal nobody has watched fail is one nobody
knows works.

**The wrapper walk is bounded as well as cycle-checked.** With only the cycle
check, removing it makes the traversal run for ever — and no answer is a weaker
signal than a wrong one.

## Complexity Tracking

> No violations.
