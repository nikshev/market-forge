---
id: REQ-WP-080
title: "The overview and the chart open as a Telegram Mini App, authenticated by Telegram"
type: work-package
prd_ref: "US-002, §26.1, §27.1, §27.5, §0 secrets rule"
prd_lines: "255-257, 4319-4335, 4388-4405, 4826-4830"
phase: null
status: planned
depends_on: [REQ-WP-064, REQ-WP-074, REQ-WP-075]
tags: [telegram, web, mini-app]
hard_gated: false
---

## Requirement

PRD US-002: "as a user I want to press a button in Telegram and open the chart exactly at the
signal's timestamp with all active overlays." §27.1 gives the routes and §26 the alert whose button
carries the link. Today the link opens a browser tab. This requirement makes the same pages open
**inside Telegram** as a Mini App — the overview (`/`) and the chart (`/chart/<venue>/<symbol>`),
unchanged in what they show — the way `lexa-reader` runs, so the product can be shown on a phone
from a bot.

Four things have to be true for that to be more than a URL pasted into a WebView:

1. **The page behaves as a Mini App.** It loads Telegram's WebApp SDK, tells Telegram it is ready and
   expands, follows Telegram's light/dark theme, uses Telegram's own back button to return from a
   chart to the overview, and stops Telegram's vertical-swipe gesture from swallowing touches on the
   chart (the one thing `lexa-reader` found out the hard way). Outside Telegram the page works exactly
   as it does today.
2. **The API knows who is asking.** Telegram signs the launch data (`initData`). The API verifies it —
   HMAC-SHA256 with the key `HMAC("WebAppData", bot_token)` over the sorted `key=value` lines, compared
   in constant time, with a bounded age — on every `/api/v1` request when authentication is required.
   The bot token comes from the environment or a secret and is never in the repository (PRD's secrets
   rule). When authentication is required and no token is configured the service **refuses to start**
   rather than serve open.
3. **A link carries the chart state in.** A button opened with Telegram's `start_param` (the form a
   `t.me/<bot>/<app>?startapp=…` link takes) and a button opened with the full deep link both land on the
   same chart state: venue, symbol, timeframe, instant, mode.
4. **It is reachable at a stable HTTPS URL.** Telegram requires HTTPS. The stack gains an optional,
   off-by-default `telegram` profile with a Cloudflare Tunnel in front of the web service — no new host
   ports — and a section of `docs/deployment.md` says how to create the bot, the tunnel and set the URL.

Not here: payments, publishing the Mini App to Telegram's directory, notifying from the bot (the
alert sender exists, [[REQ-WP-008]]), and the on-chain link an alert may later carry
([[REQ-INFRA-008]]).

## Acceptance

- **Verification, against known answers.** A valid `initData` is accepted. A changed field, a wrong bot
  token, a missing hash, a missing `auth_date` and an `auth_date` older than the configured maximum or
  more than a minute in the future are each refused, each for its own reason. The signature is
  computed by an **independent implementation** (the dev tool, in another language) and the two agree:
  a verifier checked only against its own signer proves nothing.
- **The API gate.** With authentication required, a request without a valid `Authorization: tma <initData>`
  header gets 401 and **no market data**; a valid one gets today's response unchanged. With it off (the
  local default) nothing changes. `required` with no token configured refuses to start. `/readyz` and
  `/metrics` are not behind it, and are not reachable through the tunnel.
- **The page in Telegram, with a fake SDK.** Opened with a stand-in for `window.Telegram.WebApp`, the
  page calls ready and expand once, applies the theme parameters, shows the back button on a chart and
  not on the overview (and the button returns to the overview), disables vertical swipes, and attaches
  `initData` to every API request. Without the object it throws nothing and sends no header.
- **Both link forms land on the same state.** A `start_param` and the equivalent query string produce the
  same venue, symbol, timeframe, instant and mode (a test over both parsers).
- **No dev credentials in a production build.** The dev `initData` generator writes only to an ignored
  local file, and a production build is checked to contain no signed `initData`.
- **The stack and the docs.** `docker compose --profile telegram config` is valid and starts `cloudflared`
  pointing at the web service; without the profile nothing new runs; every new environment variable is in
  `.env.example` and the deployment document (the repository's existing documents test).
- **Shown, with the date.** On a phone, in Telegram, from a bot: the overview opens, a market opens its
  chart, the timeframe selector and the channel overlay work. Recorded in the outcome note with the date
  and the URL used. This needs a bot token and a tunnel the owner provides; it is the one item no test
  can stand in for.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-126-telegram-mini-app]]
- **Outcomes:** [[OUT-2026-10-03-plan-telegram-mini-app]], [[OUT-2026-10-03-spec-telegram-mini-app]], [[OUT-2026-10-03-tasks-telegram-mini-app]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Reference implementation: `/opt/lexa-reader` (`web/src/telegram.ts`, `backend/app/auth/telegram.py`,
`docs/DEPLOY.md`, `web/scripts/gen-dev-initdata.mjs`). It exchanges `initData` for tokens once; this
requirement verifies it per request instead, because the API here has no user store and a read-only
market view needs none — a decision for the plan to confirm or reverse.
