# Implementation Plan: The overview and the chart open as a Telegram Mini App, authenticated by Telegram

**Branch**: `126-telegram-mini-app` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/126-telegram-mini-app/spec.md`

## Summary

Four additions around pages that already exist, each at the one place it can be tested:

- **The gate** — one pure verifier in the API plus one path-scoped middleware over `/api/v1/`, with the
  websocket refused when authentication is required.
- **The Mini App layer** in the web app — a small SDK module that loads Telegram's script only when
  launched from Telegram, signals ready and expand, applies the theme, manages the back button,
  disables vertical swipes and puts the launch data on every API request; a `start_param` reader.
- **Signature vectors** computed by a third implementation (`openssl`) and checked by the Python
  verifier in the fast gate and by the TypeScript signer in CI — so two languages agree without
  putting Node into every commit.
- **The stack** — an off-by-default `telegram` profile with a Cloudflare Tunnel, new variables
  forwarded to the API, and a deployment-document section.

## What planning measured

**The existing token variable.** `.env.example` already has `TELEGRAM_BOT_TOKEN` for the alert sender
([[REQ-WP-008]]). The gate reuses it: two names for one secret would be two places to rotate it.

**The public surface is already narrow, by construction.** The web service's nginx proxies only
`/api/` to the API (`proxy_pass http://api:8000`, path kept). The API serves data under `/api/v1/…`
and `/readyz`, `/metrics` and `/ws/market` at the root. Through the tunnel those three are therefore
unreachable today — a property of how two files line up, which nothing tests. FR-007 gets a test over
`nginx.conf` and the route table so that it stays true.

**A path-scoped middleware covers routes added later; a per-route dependency does not.**
[[REQ-WP-072]] found that walking an app's routes naively reached 5 of 17; that lesson is why the
gate is a prefix rule and why its test asserts **how many** routes it walked.

**The web app has no theme and hard-codes the chart's colours.** There is no stylesheet; styles are
inline, and `Chart.tsx` sets colours for the layer lines and zones directly. A dark Telegram theme
would put a light chart on a dark page, so the scheme has to reach the chart as well as the page.

**`apps/web` has no `.dockerignore`.** The image build does `COPY . .`. `.gitignore` excludes
`.env.*`, so a developer's `.env.development.local` is never committed — and is copied into the
image. Vite also reads `.env.local` in a **production** build. `lexa-reader` writes its dev launch
data to `.env.local`; copied here it would put a signed launch inside a deployed bundle. So: the dev
tool writes `.env.development.local`, the code reads it only when `import.meta.env.DEV`, a
`.dockerignore` excludes `.env*`, and a test builds with a sentinel set and greps the output.

**Web tests run only in CI** ([[ADR-021]]), and the trace graph's `VERIFIES` edges come from pytest
markers. So the verifier, the gate, the nginx and compose checks and the documents test are pytest
(fast gate, and the edges); the SDK, the start-parameter reader, the TypeScript signer and the build
check are vitest (CI, and runnable locally with `make web-test`). The plan says which is which.

**Telegram's constraints on a link.** `start_param` allows letters, digits, `_` and `-`, up to 512
characters. A deep link's path and query base64url-encoded fit that alphabet; the longest realistic
one (a signal id, an ISO instant, mode and overlays) is about 200 encoded characters, and a test
asserts the bound.

## Technical Context

**Language/Version**: Python 3.12 (`mypy --strict`); TypeScript 5.6, React 18, Vite 5, vitest 2

**Primary Dependencies**: FastAPI/Starlette (existing); Telegram's `telegram-web-app.js` loaded at
runtime from `telegram.org` **only inside Telegram**; `cloudflare/cloudflared` image for the profile

**Storage**: none. Nothing is stored: no token, no user.

**Testing**: pytest (fast gate); vitest (CI and `make web-test`); `openssl` once, to make the vectors

**Constraints**: off by default; signatures never logged; identity never stored or logged

## Constitution Check

| Principle | Result |
|---|---|
| I. No look-ahead | **Untouched.** Nothing changes which data a chart reads or when. |
| VII. Live and replay are the same code | **Holds.** One page, in Telegram and out. |
| VIII. Connectors share one interface | Not engaged. |
| X. Thresholds are configuration | **Holds.** Mode, maximum age and the tunnel are variables, not literals. |
| XIV. Everything is traceable | Python and TypeScript files carry `@trace: REQ-WP-080`; pytest tests carry the marker. |

Re-checked after design: no violations; Complexity Tracking is empty.

## Decisions, and what each rejected

**D1. The gate is middleware in the API, scoped to `/api/v1/`.** Rejected: nginx `auth_request` (a
second implementation of the check in a configuration language, untestable in the fast gate, and
absent for anyone who reaches the API port); a per-route dependency (misses the route added next
month).

**D2. A pure verifier.** `verify_init_data(init_data, bot_token, now, max_age) -> LaunchData`, raising
`LaunchRefused` carrying a reason from a closed set: `missing_hash`, `bad_signature`, `missing_auth_date`,
`malformed`, `too_old`, `from_the_future`. No I/O, the clock injected, constant-time compare, the token
never in a message. The user is parsed when present and **not required**.

**D3. The websocket is refused when authentication is required** (close code 1008). The web app does
not use it, a browser cannot send an `Authorization` header on it, and carrying launch data in the URL
would put it in logs. Rejected: a `?tma=` query parameter.

**D4. Configuration.** `TELEGRAM_BOT_TOKEN` (existing); `CHANNELFLOW_TELEGRAM_AUTH` = `off` (default)
or `required`; `CHANNELFLOW_TELEGRAM_MAX_AGE_SECONDS` (default 86400, as `lexa-reader`). `required`
with no token raises at start, naming the variable. Forwarded to the `api` service explicitly,
because compose forwards only named variables.

**D5. The launch is verified per request; no tokens.** Rejected: exchanging it for a JWT as
`lexa-reader` does. That needs a signing secret, a refresh path and a user row, to protect public
read-only data.

**D6. Telegram's script loads only inside Telegram.** A launch carries `tgWebAppData` in the URL
hash; only then is the script added. A third-party request on every ordinary page load would be a
behaviour change outside Telegram, which FR-010 forbids. Rejected: the static `<script>` tag
`lexa-reader` uses; bundling an npm copy of the SDK (Telegram's guidance is the hosted script).

**D7. `start_param` is the base64url of the deep link's path and query.** Decoded, it must match a
strict pattern (`/` or `/chart/<venue>/<symbol>` with an optional query) before it replaces the
address; anything else opens the overview (FR-012). Rejected: a custom compact encoding — one more
format to keep in step with `deepLink.ts`, which already reads the query form.

**D8. Vectors from a third implementation.** `tests/vectors/telegram_init_data.json` holds launch
strings and the expected verdicts, with the signatures computed by `openssl dgst -sha256 -hmac`
(the command is recorded in the file). The Python verifier checks them in the fast gate; the
TypeScript dev signer reproduces the hashes under vitest. Rejected: a Python test that shells out to
`node` (puts Node into every commit, against ADR-021); vectors produced by the code under test.

**D9. Compose.** Service `cloudflared` under `profiles: [telegram]`, `depends_on: web`, no `ports`,
`TUNNEL_TOKEN: ${CHANNELFLOW_TUNNEL_TOKEN:-}` (empty fails visibly at start, and `:?` would break
`docker compose config` for everyone not using the profile), `TUNNEL_TRANSPORT_PROTOCOL` defaulting
to `http2` because this host blocks QUIC egress (as `lexa-reader` found).

**D10. The chart takes a colour scheme.** `Chart` gets a `scheme` prop and the page applies Telegram's
`themeParams` as CSS variables; outside Telegram the scheme is the browser's.

## Tests (written first)

**pytest (fast gate; carry the edges):** the vectors (8 variants: two accepted, six refused, six
distinct reasons); the verifier's boundaries (age, future, skew); the token never in an error or a log
record; the gate over a route walk — every `/api/v1` route walked, count asserted, each 401 unsigned
and 200 signed, and `off` unchanged; start refused for `required` with no token; websocket refused;
`nginx.conf` proxies only `/api/` and `/readyz` `/metrics` are not under it; the compose profile
(`ports` absent, `depends_on`, off without the profile); every new variable in `.env.example` and the
deployment document.

**vitest (CI; `make web-test`):** the SDK with a stand-in `WebApp` (ready and expand once, theme,
back button by route, vertical swipes, header on every request) and without one (no header, no throw,
no script requested); `start_param` and the query yield one state; an unreadable one opens the
overview; the 512-character bound; the TypeScript signer reproduces the vectors; a production build
with a sentinel in `VITE_DEV_INITDATA` contains no sentinel.

## Project Structure

```text
src/channelflow/api/telegram_auth.py        # verifier + gate (new)
src/channelflow/api/app.py  settings.py  main.py   # wiring (changed)
apps/web/src/telegram.ts  theme.ts  startParam.ts  # Mini App layer (new)
apps/web/src/api.ts  Chart.tsx  main.tsx           # header, scheme, init (changed)
apps/web/scripts/gen-dev-initdata.mjs  apps/web/.dockerignore
tests/vectors/telegram_init_data.json
tests/unit/api/test_telegram_auth.py  test_telegram_gate.py  tests/unit/deploy/test_telegram_profile.py
apps/web/src/__tests__/telegram*.test.ts(x)  startParam.test.ts  buildHasNoInitData.test.ts
docker-compose.yml  .env.example  docs/deployment.md
```

## Complexity Tracking

Empty.
