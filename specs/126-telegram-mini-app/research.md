# Research: Telegram Mini App

## R1. What does `lexa-reader` do, and what carries over?
React + Vite SPA, Caddy, Cloudflare Tunnel (`docker-compose.cloudflare.yml`), backend verifies `initData`
(`backend/app/auth/telegram.py`: HMAC-SHA256 key `HMAC("WebAppData", token)`, sorted data-check-string,
`compare_digest`, 24 h max age, −60 s skew), exchanges it for tokens in a database. Carries over: the
algorithm, the swipe lesson (`disableVerticalSwipes`), a dev signing tool, the tunnel with
`TUNNEL_TRANSPORT_PROTOCOL: http2`. Does not: tokens, users, a database. **Decision:** verify per request.

## R2. Which routes does the API serve, and which can the tunnel reach?
`/api/v1/*` (data), `/readyz`, `/metrics`, `/ws/market`. The web nginx proxies `/api/` only, keeping the
path, so only `/api/v1/*` is reachable through it. **Decision:** gate by the `/api/v1/` prefix, test the
nginx file so the narrowness is a checked property, refuse the websocket when required.

## R3. Will a prefix rule really cover every data route?
A walk of `app.routes` reaches 5 of 17 ([[REQ-WP-072]]'s measurement); the way in is
`include_router`'s `original_router`. **Decision:** the test walks that way and asserts the count.

## R4. Where does a dev launch string end up in a deployed build?
Vite loads `.env.local` in production builds too; `apps/web` has no `.dockerignore`, so `COPY . .`
takes any local `.env*`. **Decision:** the dev tool writes `.env.development.local`; the code reads the
variable only under `import.meta.env.DEV`; a `.dockerignore` excludes `.env*`; a test builds with a
sentinel and greps `dist`.

## R5. How is "two implementations agree" tested without Node in every commit?
ADR-021 keeps `npm` out of the commit hook. **Decision:** committed vectors whose hashes come from
`openssl`; pytest checks the Python verifier against them in the fast gate, vitest checks the TS signer
against them in CI. Three implementations, none of them testing only itself.

## R6. Is Telegram's script needed on every page load?
It defines `window.Telegram.WebApp`. A launch from Telegram puts `tgWebAppData` in the URL hash.
**Decision:** load the script only when the hash carries it, so an ordinary browser makes no third-party
request (FR-010).

## R7. What can a `start_param` carry?
Letters, digits, `_`, `-`; ≤ 512 characters. **Decision:** base64url of the deep link's path and query;
the longest realistic link is about 200 characters encoded, and a test asserts it stays under 512.

## R8. Does the chart need to know about the theme?
`Chart.tsx` hard-codes colours. **Decision:** a `scheme` prop and a dark palette; the page sets Telegram's
`themeParams` as CSS variables.
