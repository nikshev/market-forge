---
id: OUT-2026-09-08-spec-binance-connector
step: spec
records: [REQ-WP-003]
commit: null
---

## What was done

Specified REQ-WP-003 as `specs/005-binance-connector/spec.md`: 18 functional
requirements, 8 success criteria, three user stories.

The fixtures and ADR-004 were produced before this step rather than after. That
is out of the pipeline's usual order and deliberate: the spec's scope depends
on what the venue actually delivers to this network, and writing it first would
have meant specifying liquidations that cannot be recorded.

## What was decided

- **Liquidations are excluded, and the reason is stated.** REQ-WP-003 asks for
  them "when available from the venue". Probing established that futures
  `@forceOrder`, `@aggTrade` and `@markPrice` connect from this network and stay
  silent, while futures `@depth` and every spot stream deliver normally. Mark
  price, funding and open interest therefore come from futures REST. Claiming a
  liquidation path with no fixture behind it would be exactly the untested
  assertion this project keeps removing.
- **Three clocks, two fields.** A Binance trade carries a trade time and a
  venue push time, and we add receipt time. `EventMeta` has `event_time_ns` and
  `ingest_time_ns`. Ruled: trade time is the event time, our receipt is the
  ingest time, and the push time is discarded. It measures venue-side latency,
  nothing requires that yet, and widening a model ADR-003 has just fixed would
  be speculative. The raw value stays in the committed fixtures, so this is
  reversible without re-recording — which is the property that makes discarding
  it acceptable rather than lossy.
- **Transport separated from logic.** Normalization and book reconstruction are
  pure; the socket is thin. That separation is what makes SC-008 — no network in
  any test — achievable rather than aspirational, and it is why PRD §35.6's
  "replay sample messages" is possible at all.
- **The book must refuse, not degrade.** FR-010 and SC-006 make an invalid book
  decline to supply state rather than returning its last good contents. PRD
  §11.1 rule 6 forbids emitting features from a stale book; a book that answers
  anyway leaves that rule to every caller to remember.
- **Unknown fields fail loudly** (FR-007). A venue that adds a field must break
  the connector on purpose. Silently ignoring it is how a connector passes its
  tests and reports wrong prices.

## What is still open

- **Rate limiting is not implemented.** PRD §35.6 lists it among connector
  concerns. Polling intervals are configuration here, and no requirement states
  a limit to respect. It needs its own requirement.
- **The venue push timestamp.** If latency research ever needs to separate
  venue-side from network-side delay, `EventMeta` will need a third field and
  ADR-003 will need amending. Recorded so the choice is visible then.
- **Whether spot and futures need separate normalizers.** The recorded fixtures
  show their depth and trade shapes agreeing, so one is assumed. A futures-only
  field appearing later would change that.
