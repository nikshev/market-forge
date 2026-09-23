---
id: SPEC-121-multi-venue-ingest
requirement: REQ-WP-076
speckit_path: specs/121-multi-venue-ingest/spec.md
status: draft
---

## Summary

§5.2's Phase 2 universe adds Bybit and OKX, and §6.2's shape says one ingest
service per venue. The policies and normalisers for both exist and were
measured; the live path does not — it is Binance code with the venue written in
three places, and Binance's "subscriptions in the URL" is not a shape that
generalises: Bybit V5 and OKX v5 subscribe by a message after connecting. The
spec makes the venue a value carried through builder, session, policy, archive
prefix and the `venue` column, requires each venue's own stream and subscribe
rule pinned against its documentation rather than substituted into Binance's,
and requires a connection that delivers nothing to be **reported** — the
failure that motivated the requirement, found the first time by measurement
rather than by a message.

## Links

- Requirement: [[REQ-WP-076]]
- Depends on: [[REQ-WP-066]]
