# Implementation Plan: CUSTOM_ACCOUNTING pools are quoted, never curved

**Branch**: `wp-071-v4-quoting` | **Date**: 2026-09-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/112-v4-executable-quoting/spec.md`

## Summary

PRD §18.8.1 forbids the standard curve for `CUSTOM_ACCOUNTING` pools and asks for
an executable quoting adapter instead. [[REQ-WP-047]] built the classification;
this builds the quote.

The approach has one idea in it: **the replay seam is the RPC provider, not the
adapter.** There is exactly one quoting code path, and CI runs it against a
provider that answers `eth_call` from the captured fixture. So the encoder, the
ABI decoder and the revert unwrapping are all exercised offline, and an encoding
bug surfaces as a fixture miss rather than as a different-but-plausible number.
That is Constitution VII taken literally rather than approximated with two
parallel implementations.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `eth_hash` (keccak, for selectors) — already a
dependency. No new ones.

**Storage**: N/A. The fixture is a file; nothing is persisted.

**Testing**: pytest, `@pytest.mark.trace("REQ-WP-071")`, mutation sweep via
`tools/mutate.py`

**Target Platform**: library code under `src/channelflow/dex/`

**Project Type**: single project

**Performance Goals**: N/A — one `eth_call` per quote; the cost is the node's.

**Constraints**: `mypy --strict` over `src/`; the unit suite makes no network
calls; every source file carries `# @trace: REQ-WP-071`.

**Scale/Scope**: four pools in the fixture, 20 captured answers, one new module.

## What the curve says today, measured

Built a `PoolState` from the fixture's own `state` record for pool
`0xf7caa8ee…` and asked `depth_to_bps(bps=50, upward=True)`:

    reachable: False
    amount0: 0   amount1: 0
    reason: "the pool has no active liquidity, so its price cannot be moved"

The same pool, same block, absorbs 1 ETH for 496412035653451820217981817 units.

Note what `require_tick_map_complete` does here: it **passes**. The tick map is
empty and the pool reports zero liquidity, so `0 == 0` and the map explains the
pool perfectly. [[REQ-WP-060]]'s guard is not weak — it is answering a different
question, and correctly. Nothing in the tick path can see this, which is why the
gate must be on the class, before the state is ever built.

## Constitution Check

*GATE: passed before Phase 0, re-checked after Phase 1.*

| Principle | How this plan satisfies it |
|---|---|
| I. No look-ahead | A quote is stamped with the block it was taken at. A source asked for a block it does not hold raises rather than serving a later one. |
| II. Time is not one thing | A quote carries a block height, not a timestamp, and never a wall clock. |
| VI. Every feature documented | The refusal reasons, the units of `amount_out` and the direction convention are stated on the types. |
| VII. Live and replay are the same code | One adapter, one encoder, one decoder. The seam is `ChainDataProvider`; replay is a provider, not a second adapter. |
| VIII. Connectors share one interface | The live side implements the existing `ChainDataProvider` protocol rather than a new one. |
| X. Thresholds are configuration | The quoter address and the ladder sizes are arguments. Nothing numeric is compiled in except ABI constants and the `UnexpectedRevertBytes` unwrapping, which are the chain's, not ours. |
| XII. Correctness precedes performance | No batching, no caching. One call per quote. |
| XIV. Everything is traceable | `# @trace: REQ-WP-071` on both new source files; markers on every test. |

No violations. Complexity Tracking is therefore empty and omitted.

## Project Structure

### Documentation (this feature)

```text
specs/112-v4-executable-quoting/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── quote-source.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/channelflow/
├── chain/
│   └── providers.py          # MODIFY: add CallReverted(RuntimeError) with .data
└── dex/
    ├── uniswap_v4.py         # MODIFY: CURVE_RECONSTRUCTIBLE, CurveDoesNotApply,
    │                         #         require_curve_applies
    ├── v4_quoting.py         # CREATE: the adapter
    └── __init__.py           # MODIFY: exports

tests/
├── unit/dex/
│   ├── test_v4_quoting.py    # CREATE
│   └── test_uniswap_v4.py    # MODIFY: the gate
└── fixtures/uniswap_v4/
    └── quotes.jsonl          # already captured and committed
```

**Structure Decision**: the adapter is a new module in the existing
`channelflow.dex` package, beside `uniswap_v4.py`, which keeps v4's routing and
classification where they are and adds pricing next to them. The replay provider
lives in the test tree, not in `src/`: it is a test double for a protocol `src/`
already defines, and shipping it would invite production code to depend on a
fixture.
