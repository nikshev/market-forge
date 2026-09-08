---
traces: [REQ-ASSET-001]
status: draft
---

# Feature Specification: Asset identity registry

**Feature Branch**: `asset-001-registry`

**Created**: 2026-09-08

**Status**: Draft

**Input**: REQ-ASSET-001 — PRD §18.13's asset registry. Acceptance criteria
derived and approved in
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Say that two things are the same asset, deliberately (Priority: P1)

Native ETH, WETH on Ethereum, WETH on Base and a Hyperliquid ETH market are
four representations of one economic asset, and each says so explicitly.

**Why this priority**: PRD §18.13 opens with the reason the registry exists —
"Cross-chain/venue comparison is impossible without a strict asset registry" —
and every consensus price and basis figure downstream rests on the claim that
the venues being compared are quoting the same thing.

**Independent Test**: Register the PRD's own ETH example and assert the four
representations resolve to one canonical asset.

**Acceptance Scenarios**:

1. **Given** a canonical asset, **When** representations are registered against it, **Then** each carries chain id, contract address or a native marker, decimals, and its wrapper/underlying relationship.
2. **Given** a representation, **When** its canonical asset is read, **Then** it is the one declared, never inferred.
3. **Given** two representations of one asset, **When** they are compared, **Then** they are recognised as the same economic asset.

---

### User Story 2 - Never merge two assets because they share a ticker (Priority: P1)

Two tokens called WETH on different chains are different representations. Two
tokens called USDC from different bridges are different assets unless something
says otherwise.

**Why this priority**: PRD §18.13's own prohibition — "Do not merge wrapped,
bridged or synthetic assets only by ticker" — and the failure it prevents is
silent. A consensus price computed across a real asset and a bridged
lookalike is a number with no meaning, and it looks like every other number.

**Acceptance Scenarios**:

1. **Given** two representations sharing a ticker but differing in chain, **When** they are resolved, **Then** they remain distinct representations.
2. **Given** two representations sharing a ticker and chain but differing in contract, **When** they are resolved, **Then** they remain distinct.
3. **Given** a representation with no declared canonical asset, **When** it is registered, **Then** it is refused.
4. **Given** a lookup by ticker alone, **When** more than one asset uses it, **Then** the lookup refuses rather than choosing.

---

### User Story 3 - Tell "does not apply" from "we do not know" (Priority: P1)

A native asset has no bridge issuer. A bridged asset whose issuer nobody
recorded has an unknown one. These are different facts and the registry says
which.

**Why this priority**: the criterion that most affects what downstream trusts.
Conflating the two means a consensus price will one day include an asset whose
provenance nobody checked, and nothing will have said so.

**Acceptance Scenarios**:

1. **Given** a native asset, **When** its bridge issuer is read, **Then** it is explicitly not applicable.
2. **Given** a bridged asset whose issuer was never recorded, **When** it is read, **Then** it is explicitly unknown.
3. **Given** either state, **When** a consumer filters on it, **Then** the two are distinguishable without inspecting anything else.
4. **Given** a representation, **When** it is registered without stating which, **Then** it is refused.

---

### User Story 4 - Know which venue a pair trades on, and what kind it is (Priority: P2)

A market pair names its base and quote representations and its venue; a venue
names its kind, and an on-chain venue names its protocol deployment.

**Why this priority**: PRD §18.13's `MarketPair` and `Venue`, and the
distinction §18.14 rests on — an order book and an AMM are not compared the
same way, so the registry has to say which a venue is.

**Acceptance Scenarios**:

1. **Given** a market pair, **When** it is read, **Then** it names base and quote representations and a venue.
2. **Given** an order-book venue, **When** its kind is read, **Then** it is an order book, and it has no protocol deployment.
3. **Given** an AMM venue, **When** its kind is read, **Then** it is an AMM pool and it names its protocol deployment.
4. **Given** a market pair whose base and quote are the same representation, **When** it is registered, **Then** it is refused.

---

### User Story 5 - Rank sources, and say how sure you are (Priority: P2)

Every mapping carries a confidence and a pricing source priority, both readable.

**Why this priority**: PRD §18.13 lists both among the required fields. Their
consumer is the consensus price, which has to decide which venues to trust.

**Acceptance Scenarios**:

1. **Given** a mapping, **When** its confidence is read, **Then** it is a value between 0 and 1.
2. **Given** several representations of one asset, **When** they are ordered by pricing source priority, **Then** the ordering is total and stable.
3. **Given** a mapping registered without a confidence, **When** it is registered, **Then** it is refused.

---

### Edge Cases

- What happens when the same representation is registered twice? The second registration is refused: a chain id and contract address identify one token, and a repeat means two sources disagree about it.
- What happens when a representation declares a canonical asset that is not registered? It is refused — a dangling reference here would surface later as a consensus price over an asset nobody defined.
- What happens when a wrapper points at an underlying that is itself a wrapper? Allowed, and the chain is resolvable to its root — wrapped-bridged tokens exist.
- What happens when a wrapper chain contains a cycle? The build refuses, naming the cycle.
- What happens when a stablecoin family is asked of a non-stablecoin? Explicitly not applicable, the same three-state answer as the bridge issuer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A representation MUST carry chain id, contract address or a native marker, decimals, and its wrapper/underlying relationship.
- **FR-002**: A representation MUST declare its canonical asset; none is inferred.
- **FR-003**: A representation whose declared canonical asset is not registered MUST be refused.
- **FR-004**: Two representations differing in chain or contract MUST remain distinct, whatever their tickers.
- **FR-005**: A lookup by ticker alone MUST refuse when more than one asset uses that ticker.
- **FR-006**: Registering the same chain id and contract address twice MUST be refused.
- **FR-007**: Bridge issuer and stablecoin family MUST each be a value, explicitly not applicable, or explicitly unknown — never merely absent.
- **FR-008**: A representation registered without stating which of those three MUST be refused.
- **FR-009**: A wrapper chain MUST resolve to its root, and a cycle MUST be refused.
- **FR-010**: A market pair MUST name base and quote representations and a venue, and MUST refuse when base and quote are the same.
- **FR-011**: A venue MUST name its kind, and an on-chain venue MUST name its protocol deployment.
- **FR-012**: Every mapping MUST carry a confidence in [0, 1] and a pricing source priority, both readable, with no default for either.
- **FR-013**: Ordering representations by pricing source priority MUST be total and stable.
- **FR-014**: No module may consult a system clock or perform network I/O.

### Key Entities

- **Asset**: a canonical economic thing, independent of where it is held.
- **Asset representation**: one concrete token or market standing for that asset on one chain or venue.
- **Market pair**: two representations traded against each other somewhere.
- **Venue**: where trading happens, and what kind of place it is.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: PRD §18.13's ETH example registers, and its four representations resolve to one asset.
- **SC-002**: Representations sharing a ticker but differing in chain or contract stay distinct.
- **SC-003**: A representation without a declared canonical asset is refused.
- **SC-004**: An ambiguous ticker lookup refuses.
- **SC-005**: A duplicate chain-and-contract registration is refused.
- **SC-006**: Not-applicable and unknown are distinguishable for both three-state fields, and omitting them is refused.
- **SC-007**: A wrapper chain resolves to its root; a cycle is refused.
- **SC-008**: A market pair with identical base and quote is refused.
- **SC-009**: An on-chain venue without a protocol deployment is refused.
- **SC-010**: Ordering by pricing source priority is total and stable, and a missing confidence is refused.
- **SC-011**: No module references a clock or an HTTP client.

## Assumptions

- **`Pool` and `ProtocolDeployment` are referenced, not rebuilt.** REQ-WP-015's `PoolState` and REQ-WP-014's `RegistryEntry` already model them; the registry names a deployment by protocol, version and address rather than duplicating the decoder registry.
- **No discovery.** PRD §18.5's pool and protocol discovery registry is not built; representations are supplied.
- **No pricing.** §18.16's USD valuation policy is a separate concern; this registry says which things are the same, not what they are worth.
- **No storage.** In memory, as everywhere else.
