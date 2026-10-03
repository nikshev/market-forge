---
id: OUT-2026-10-03-plan-markets-registered
step: plan
records: [REQ-WP-081]
commit: null
---

## What was done

Planned the registration as `specs/127-markets-registered/`, after reading the registry, the Binance URL
builder, the repository's `add_market`, the markets schema and the page.

## What was decided

- **The type is a function of the symbol, not a constant per venue.** A constant is right for Binance and
  Bybit and wrong for OKX the day its instrument stops being a swap; the same class of fault as calling
  spot "perp", arriving a month later. OKX reads the suffix and refuses a form it does not recognise.
- **A test ties the type to the endpoint the daemon really uses**, so that Binance's URL changing to a
  futures one fails a test until the type is reconsidered.
- **The no-rules row moves beside `market_row`.** Ingest must not import the API; two definitions of "a
  market with no rules" would drift, and one of them is already inline in the API.
- **Idempotence by reading first**, not by appending and relying on the read's dedupe: one more row per
  restart, forever, in an append-only table.
- **`setup-plan.sh` followed `.specify/feature.json`, which still pointed at the previous feature.** It
  would have written this plan into the wrong directory had that file not already existed; the pointer was
  corrected before planning. (The pointer is local and ignored by git, which is why nothing reset it.)

## What is still open

- Whether five threads on SQLite hit "database is locked" often enough that the concurrency test belongs
  only in the integration set (tasks decide after trying).
- Branding: the overview still says "ChannelFlow".
