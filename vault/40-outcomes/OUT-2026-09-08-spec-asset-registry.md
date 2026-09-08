---
id: OUT-2026-09-08-spec-asset-registry
step: spec
records: [REQ-ASSET-001]
commit: null
---

## What was done

`specs/022-asset-registry/spec.md`: five user stories, 14 functional
requirements, 11 success criteria, two ADRs.

## What was decided

- **Identity is declared, never inferred** ([[ADR-038]]). §18.13's prohibition
  is easy to agree with and easy to violate: a helper taking `"USDC"`, a dict
  keyed on symbol, a fallback resolving "by name" — each is merging by ticker
  with extra steps. So the ticker lookup refuses when ambiguous, and there is
  no code path that resolves a representation any other way.
- **Bridge issuer and stablecoin family are three-state** ([[ADR-037]]). A
  native asset has no bridge issuer; a bridged asset whose issuer nobody
  recorded has an unknown one. With one `None` for both, "every representation
  in this consensus has a known or inapplicable issuer" is not expressible —
  and that is the statement a consensus price needs to make about its inputs.
- **`Pool` and `ProtocolDeployment` are referenced, not rebuilt.** REQ-WP-015's
  `PoolState` and REQ-WP-014's `RegistryEntry` already model them.

## What is still open

- **No discovery** (§18.5); representations are supplied.
- **No pricing** (§18.16); the registry says which things are the same, not
  what they are worth.
