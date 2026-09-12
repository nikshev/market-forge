---
traces: [REQ-WP-058]
status: draft
---

# Feature Specification: A HyperEVM pool is decoded as the protocol it is

**Feature Branch**: `wp-058-hyperevm-decoders`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-058 — PRD §18.11.2's protocol-specific pool events and
cross-layer transfers, through §18.6's decoder registry.

## Context

PRD §18.11.2 ends with "A HyperEVM AMM is analyzed according to **its AMM
protocol**". Measured on chain 999 on 2026-09-12, that sentence is not a
formality: the two busiest WHYPE/USDC pools emit the identical `Swap` topic0
with the identical payload and belong to different protocols.

    pool          factory       state call      fee
    0x6c9a33e3…   0xff7b3e8c…   slot0()         fee() = 500, immutable
    0xbe512f58…   0xf77bd082…   globalState()   per swap, via a Fee(uint16) log

Over 900 captured blocks the Algebra pool's own `fee()` reads 1069; its thirty
swaps carry 1069, 1070 and 1071. Twenty-six of the thirty are wrong when priced
from the pool's fee, each by less than two tenths of a percent. The `Fee` log
sits 3, 6, 7 or 10 log indices before the swap it prices, so pairing is
positional or it is wrong.

The second half is the same shape. A cross-layer transfer is an ERC-20
`Transfer` to a code-less system address `0x2000…0000 + index`; the amount is in
EVM units and HyperCore credits it divided by `10^evm_extra_wei_decimals`,
which ranges from −2 to +13 across the 170 spot assets that have an EVM
contract.

Neither error produces an exception. Both produce a believable number.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The protocol comes from the registry (Priority: P1)

A researcher ingests logs from both pools. Each swap is attributed to the
protocol its registry entry names, not to whichever decoder recognises the
signature. A log from an address no entry covers yields no event and a stated
reason, and the raw record is retained.

**Acceptance**: decoding the captured logs of both pools yields events labelled
`uniswap_v3` and `algebra_integral` respectively; a record from an unregistered
address yields zero events and a failure whose reason names the gap.

### User Story 2 - An unknown fee is unknown (Priority: P1)

An Algebra swap arrives without the `Fee` log of its transaction — a log
filtered by pool address does not carry it. The swap decodes, and its fee is
absent. Nothing substitutes the pool's current fee or zero.

**Acceptance**: the decoded event has no fee; asking for one raises rather than
returning a default; pairing the swap with its transaction's `Fee` log produces
the fee that log carries, and a transaction holding two swaps pairs each with
the fee published for it.

### User Story 3 - The amounts are checkable without a node (Priority: P1)

Every captured swap reconciles against the ERC-20 transfers of its own
transaction, offline, with no archive node and no trust in one endpoint.

**Acceptance**: all 164 moving sides of the 83 captured swaps equal the pool's
nearest preceding transfer of that token in the transaction. The two sides that
moved nothing are reported as unverifiable, and their count is asserted.

### User Story 4 - A transfer resolves to a HyperCore asset and amount (Priority: P1)

A transfer to a system address resolves to the spot asset its index names and
to the amount HyperCore credits.

**Acceptance**: all 44 captured transfers resolve to the asset `spotMeta` names
at that index; the converted amount uses the asset's `evm_extra_wei_decimals`;
a remainder below HyperCore's resolution is reported, not dropped; an ordinary
address resolves to nothing rather than to index zero.

### Edge Cases

- A transaction where the pool also flashes or collects: netting the whole
  receipt disagrees with the event.
- A swap with `amount1 = 0`: nothing settles that side, and the nearest
  preceding transfer belongs to the previous operation.
- A transaction with two swaps on one pool: the later swap's settling transfers
  appear after the earlier swap's log.
- `0x2000…0000` itself is index 0, a real asset (USDC) and not a sentinel.
- A tick is `int24` sign-extended across a full word; reading the low three
  bytes as two's complement yields a large positive tick instead of a small
  negative one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pool family is decided by factory address, from a registry.
  An unknown factory is refused, never defaulted.
- **FR-002**: Both families share one payload decoder: `amount0`, `amount1`,
  `sqrtPriceX96`, `liquidity`, `tick`, with `int24` sign-extended.
- **FR-003**: A Uniswap v3-style swap carries the fee its registry entry
  records, which is immutable for the pool.
- **FR-004**: An Algebra swap carries no fee unless the `Fee` log of its own
  transaction is supplied.
- **FR-005**: Pairing selects the last `Fee` log preceding the swap's log index
  within the same transaction, at whatever distance.
- **FR-006**: Each decoder implements `ProtocolDecoder` and is selected through
  `DecoderRegistry`, so §18.6's ABI fail-closed applies unchanged.
- **FR-007**: A system address is recognised by prefix and resolved to
  `int(address) - 0x2000…0000`; any other address resolves to nothing.
- **FR-008**: Converting an EVM amount to HyperCore units divides by
  `10^evm_extra_wei_decimals` and reports quotient and remainder separately.

### Key Entities

- **PoolFamily** — `uniswap_v3` or `algebra_integral`.
- **HyperEvmSwap** — the decoded payload plus the pool and an optional fee.
- **CoreAsset** — a HyperCore spot asset: index, EVM contract, decimals.
- **CrossLayerTransfer** — direction, asset, EVM amount, credited amount,
  remainder.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 164 of 164 moving swap sides reconcile against their
  transaction's transfers; the 2 non-moving sides are reported as such.
- **SC-002**: 30 of 30 Algebra swaps pair with a published fee, and 26 of them
  differ from the pool's own `fee()`.
- **SC-003**: 44 of 44 captured transfers resolve to the asset `spotMeta` names
  at the system address's index.
- **SC-004**: Mutating the sign extension, the pairing direction, the family
  lookup or the decimal exponent is caught by a test.

## Assumptions

- The two captured pools are representative of the two families present. 130
  addresses emitted the shared topic0 over 800 blocks; only these two are
  registered, and an unregistered one decodes to nothing by design.
- `spotMeta` is the authority for a spot asset's index and decimals.

## Open Questions

- The HyperCore→HyperEVM direction has no fixture: all 44 captured transfers
  move toward HyperCore.
- Pool state reconstruction is out of scope and blocked on an archive node
  (ADR-067).
