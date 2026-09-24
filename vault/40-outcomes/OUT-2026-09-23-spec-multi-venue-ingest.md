---
id: OUT-2026-09-23-spec-multi-venue-ingest
step: spec
records: [REQ-WP-076]
commit: null
---

## What was done

[[REQ-WP-076]] specified as `specs/121-multi-venue-ingest/spec.md`, `traces:
[REQ-WP-076]`; note visible as [[SPEC-121-multi-venue-ingest]].

## What was decided

**The venue becomes a value, and the seam must not assume URL-only
subscriptions.** This is the sentence the whole requirement turns on. Binance
carries streams in the URL; Bybit V5 and OKX v5 subscribe by a message after
connecting. `WebsocketTransport`'s current `url_for(streams)` fits one venue, so
"make the venue a value" is a change of what connecting means, not a rename.
The spec fixes that the venue's rule travels through the live path and is
pinned by tests; *which layer assembles the subscription* is deliberately left
to planning.

**Each venue's strings are asserted against that venue's documentation.** §46
names Bybit's orderbook WebSocket and OKX's v5 API, and the requirement says
Binance's `@aggTrade` notation is not assumed to generalise. FR-002 makes the
documentation the authority in the test, not a Binance string with parts
replaced.

**Silence is a reported condition, not an absence of data.** The motivating
incident: an upper-case stream name on Binance's combined stream connected and
delivered nothing, found by measurement. FR-006 requires a named report within
a configurable window, and requires it *not* to fire for a normal quiet window.

**The existing deployment is frozen.** FR-009 and SC-005: Binance's stream
name, URL and policy are byte-identical before and after, proven by its
existing tests passing unchanged. A multi-venue refactor that alters the venue
already in production would be two changes wearing one requirement.

**Live verification is not a CI gate.** A third-party venue in the fast gate
would make every commit depend on someone else's uptime, which
[[REQ-INFRA-002]] exists to avoid; the spec puts the real-connection check in
the quickstart and keeps the suite on fakes and documented strings.

**Symbol spellings are configured as the venue writes them.** No cross-venue
symbol mapping is introduced; a wrong spelling surfaces as the silence report
rather than as a guessed translation — §17 owns mapping.

## What is still open

- **Which layer assembles a subscribe message** — transport, session or a venue
  object — is the central planning decision this spec leaves open on purpose.
  The constraint is recorded: the answer must serve three venues whose
  mechanics differ, not the one whose mechanics happen to be implemented.
- **The upper-case failure's root cause is still an open question of UX**, not
  of this spec: the silence report will surface it, but whether a stream name
  should be validated before connecting (fail fast) or observed after (report)
  is a planning choice with a real cost either way.
- **The connect rate limits remain conservative guesses**, as
  `session.py` already documents; establishing them means deliberately
  exceeding a venue's cap, which this feature does not do.