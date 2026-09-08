---
id: OUT-2026-09-08-implement-asset-registry
step: implement
records: [REQ-ASSET-001]
commit: null
---

## What was done

`channelflow.assets`: PRD §18.13's entities and the registry that refuses
everything the section forbids. 25 tests, built against the PRD's own ETH
example.

## A guard whose removal produced no answer

The wrapper traversal was cycle-checked with a seen-set. Removing that check
does not make the walk wrong — it makes it run for ever, and the sweep hung
until it was killed. That is the second time in this repository (REQ-WP-018's
width budget was the first), and no answer is a much weaker signal than a wrong
one: it is indistinguishable from a passing suite until the process stops
responding.

The walk is now **bounded as well as cycle-checked**. A chain deeper than 32
hops refuses by depth; a chain that loops refuses by the seen-set. Each guard
has its own test, and removing either fails that test in milliseconds — checked
both ways round, so neither hides the other's absence.

The sweep also uses a bounded runner now, which reports `HUNG` as a result
rather than waiting.

## What was decided

- **Every refusal has a test that constructs the violation.** This module is
  almost entirely refusals, and a refusal nobody has watched fail is one nobody
  knows works.
- **The fixture is PRD §18.13's own example** — native ETH, WETH on Ethereum,
  WETH on Base, a Hyperliquid representation — so the central test is a reading
  of the section rather than an invention.
- **The USDC test is the one the prohibition is actually about.** Two tokens
  called USDC with different depeg risk: a consensus across both reports
  agreement that does not exist, and the number looks like every other number.
- **An order-book venue carrying a protocol deployment is refused too.** The
  obvious direction is the on-chain one; the reverse matters because accepting
  it would let a CEX masquerade as on-chain, and §18.14 compares the two
  differently.

## Mutation results

Eight mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| An ambiguous ticker returns the first match | `test_an_ambiguous_ticker_lookup_refuses` |
| A dangling canonical asset is accepted | `test_a_representation_naming_an_unregistered_asset_is_refused` |
| A duplicate representation overwrites the first | `test_registering_the_same_chain_and_contract_twice_is_refused` |
| `same_asset` falls back to comparing tickers | `test_the_prds_own_eth_example_resolves_to_one_asset` (+1) |
| The cycle guard is removed | `test_a_wrapper_cycle_is_refused` |
| The depth bound is removed | `test_a_chain_deeper_than_any_real_wrapping_is_refused` |
| The three-state fields get a default | `test_omitting_a_three_state_field_is_refused` |
| Priority ordering loses its tie-break | `test_a_tie_in_priority_is_broken_by_key` |

The fourth is the one §18.13 is written against: falling back to ticker
comparison passes casual inspection and merges a bridged token with the real
one.

## What is still open

- **`REQ-WP-016` is next** and depends on this.
- **No discovery** (§18.5) and **no pricing** (§18.16).
- **The registry holds no data.** It is a structure and its rules; populating it
  for real venues is operational work.
