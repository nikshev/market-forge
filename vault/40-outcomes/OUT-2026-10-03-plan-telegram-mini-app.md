---
id: OUT-2026-10-03-plan-telegram-mini-app
step: plan
records: [REQ-WP-080]
commit: null
---

## What was done

Planned the Mini App as `specs/126-telegram-mini-app/` (plan, research, data model, two contracts,
quickstart), after reading the existing web app, the API factory, nginx, the Dockerfile and compose.

## What was decided

- **The gate is middleware scoped to `/api/v1/`, not nginx `auth_request` and not a per-route
  dependency.** nginx would be a second implementation in a language the fast gate cannot test and
  would not protect anyone who reaches the API port; a per-route dependency misses the next route.
  The test walks the routes and asserts how many it walked, because [[REQ-WP-072]] found a naive walk
  reaches 5 of 17.
- **The websocket is refused when authentication is required.** A browser cannot send an
  `Authorization` header on one, the page does not use it, and launch data in a URL lands in logs.
- **The existing `TELEGRAM_BOT_TOKEN` is reused**, not a second name for the same secret.
- **A dev launch string must not reach a deployed bundle — and by default it would have.** Vite reads
  `.env.local` in production builds and `apps/web` has no `.dockerignore`, so `lexa-reader`'s pattern
  copied here would bake a signed launch into the image. The tool writes `.env.development.local`, the
  code reads it only under `import.meta.env.DEV`, a `.dockerignore` excludes `.env*`, and a test builds
  with a sentinel and searches the output.
- **Telegram's script loads only inside Telegram.** A static tag would make every ordinary page load
  call out to `telegram.org`, a behaviour change FR-010 forbids.
- **Three implementations of the signature, no Node in the commit hook.** Vectors computed with
  `openssl`; pytest checks the Python verifier in the fast gate, vitest the TypeScript signer in CI.
- **`start_param` is the base64url of the deep link**, validated against a strict pattern before it
  replaces the address.
- **`:?` was not used for the tunnel token**, because it would make `docker compose config` fail for
  everyone not using the profile; an empty token makes `cloudflared` fail visibly instead.

## What is still open

- Whether the chart's dark palette needs more than the layer lines and zones (planning read
  `Chart.tsx` for the hard-coded colours; the tasks check the rest by looking at it).
- The tunnel token, the domain and the bot token: not requested here; they gate SC-005 only.
- Web tests are CI-only by ADR-021, so the page's behaviour is verified there and the trace edges come
  from the Python tests; the tasks must say which tests carry which acceptance line.
