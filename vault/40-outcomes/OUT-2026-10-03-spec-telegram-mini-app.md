---
id: OUT-2026-10-03-spec-telegram-mini-app
step: spec
records: [REQ-WP-080]
commit: null
---

## What was done

Specified [[REQ-WP-080]] as `specs/126-telegram-mini-app/spec.md`: five stories, fifteen requirements.
Before writing it, `/opt/lexa-reader` was read (its Telegram SDK layer, its `initData` verifier, its
Caddy and Cloudflare Tunnel files, its dev-signing script and deployment document) and the existing
web app and API were read to see what is already there: a Vite app with the overview and the chart,
nginx proxying `/api`, and a `create_app` factory with a middleware pattern the gate can follow.

## What was decided

- **Verify per request; store nothing.** `lexa-reader` exchanges `initData` for tokens in a database.
  This API has no users and the view is read-only public data, so a signed launch is checked on every
  request. The consequence the spec draws: identity is not needed, so it is neither stored nor logged.
- **The gate is access control, not secrecy.** It stops the tunnel's address being a free read API and
  makes "opens inside Telegram" mean something. A captured launch can be replayed until it ages out;
  accepted, stated and bounded by a configurable age.
- **The websocket is a stated hole.** `/ws/market` cannot carry an `Authorization` header from a
  browser, sits outside `/api` (so the web proxy does not reach it) but is reachable if the API port is
  bound. The spec says it must be closed to an unsigned caller when authentication is required and
  leaves how to the plan.
- **Two implementations of the signature are required (FR-003).** A verifier tested only against its own
  signer proves nothing; the dev tool is in another language precisely so the two can disagree.
- **Showing it is a separate, honest item.** SC-005 needs a bot token and a tunnel only the owner has.
  The spec says so, instead of letting the build look finished without it.

## What is still open

- How the websocket is closed (plan).
- The shape of a `start_param` that carries venue, symbol, timeframe, instant and mode inside Telegram's
  alphabet and 512-character limit (plan).
- Whether the gate belongs in the API as middleware or at the edge in nginx (plan; the spec requires the
  property, not the place).
- The bot token and the tunnel token: not requested here, needed for SC-005.
