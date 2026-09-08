---
id: SPEC-022-asset-registry
requirement: REQ-ASSET-001
speckit_path: specs/022-asset-registry/spec.md
status: draft
---

## Summary

PRD §18.13's asset registry: the entities that let two venues be compared at
all, and the refusals that keep the comparison honest.

[[ADR-038]] makes identity declared rather than inferred. §18.13's prohibition —
"Do not merge wrapped, bridged or synthetic assets only by ticker" — is easy to
agree with and easy to violate, because ticker matching is what every
convenient shortcut reduces to. So a lookup by ticker refuses when ambiguous,
and a representation without a declared canonical asset is refused outright.

[[ADR-037]] makes bridge issuer and stablecoin family three-state. A native
asset has no bridge issuer; a bridged asset whose issuer nobody recorded has an
unknown one, and with a single `None` for both no consumer can tell.

## Links

- Requirement: [[REQ-ASSET-001]]
- Decisions: [[ADR-037]], [[ADR-038]]
- Feeds: [[REQ-WP-016]]
